from itertools import groupby
import calendar
import os
import time
from datetime import datetime, time as dtime, timezone as dt_timezone, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from usuarios.models import UserProfile
from .forms import ScheduleMeetingForm
from .models import Conversation, Message, Meeting


def _department_label(profile):
    # Aqui usamos company para agrupar usuários por empresa na UI.
    return (getattr(profile, "company", "") or "").strip() or "Sem empresa"


def get_or_create_conversation_between(user_a, user_b):
    qs = Conversation.objects.filter(participants=user_a).filter(participants=user_b)
    conversation = qs.first()
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.set([user_a, user_b])
    return conversation


class ChatHomeView(LoginRequiredMixin, TemplateView):
    template_name = "chat/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        online_qs = (
            UserProfile.objects.select_related("user")
            .exclude(user=self.request.user)
            .exclude(user__is_superuser=True)
            .exclude(user__username__iexact="administrator")
            .order_by("company", "department", "display_name", "user__username")
        )
        groups = []
        for dept, profiles in groupby(online_qs, key=_department_label):
            groups.append((dept, list(profiles)))
        context["online_profiles_by_department"] = groups

        conversations = (
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related("participants", "messages")
            .all()
        )
        recent_conversations = []
        for conv in conversations:
            last_msg = conv.messages.order_by("-created_at").first()
            other = conv.participants.exclude(id=self.request.user.id).first()
            if not other or other.is_superuser or other.username.lower() == "administrator":
                continue
            recent_conversations.append(
                {
                    "id": conv.id,
                    "other_id": other.id,
                    "other_name": getattr(
                        getattr(other, "profile", None), "display_name", ""
                    )
                    or other.username,
                    "last_text": last_msg.text if last_msg else "",
                    "last_time": last_msg.created_at if last_msg else conv.created_at,
                }
            )
        recent_conversations.sort(key=lambda c: c["last_time"], reverse=True)
        context["recent_conversations"] = recent_conversations
        return context


class OnlineUsersView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        profiles = (
            UserProfile.objects.select_related("user")
            .exclude(user=request.user)
            .exclude(user__is_superuser=True)
            .exclude(user__username__iexact="administrator")
            .order_by("company", "department", "display_name", "user__username")
        )
        groups = []
        for dept, prof_list in groupby(profiles, key=_department_label):
            groups.append(
                {
                    "department": dept,
                    "users": [
                        {
                            "id": p.user_id,
                            "name": p.display_name or p.user.username,
                            "status": p.status,
                        }
                        for p in prof_list
                    ],
                }
            )
        return JsonResponse({"groups": groups})


class ConversationMessagesView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, conversation_id: int, *args, **kwargs):
        after = request.GET.get("after")
        qs = Message.objects.filter(conversation_id=conversation_id)
        if after:
            qs = qs.filter(id__gt=after)
        qs = qs.select_related("sender", "sender__profile").order_by("id")

        messages = []
        for m in qs:
            attachment_url = m.attachment.url if m.attachment else ""
            attachment_name = (
                os.path.basename(m.attachment.name) if m.attachment else ""
            )
            messages.append(
                {
                    "id": m.id,
                    "text": m.text or "",
                    "attachment_url": attachment_url,
                    "attachment_name": attachment_name,
                    "sender_name": (
                        m.sender.profile.display_name or m.sender.username
                        if hasattr(m.sender, "profile")
                        else m.sender.username
                    ),
                    "is_me": m.sender_id == request.user.id,
                    "time": m.created_at.strftime("%H:%M"),
                }
            )
        return JsonResponse({"messages": messages})


class NotificationsView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs):
        unread = (
            Message.objects.filter(conversation__participants=request.user)
            .exclude(sender=request.user)
            .filter(read_at__isnull=True)
            .select_related("sender", "sender__profile")
        )
        summary = {}
        for m in unread:
            key = m.sender_id
            name = (
                m.sender.profile.display_name
                if hasattr(m.sender, "profile") and m.sender.profile.display_name
                else m.sender.username
            )
            item = summary.get(
                key,
                {
                    "user_id": m.sender_id,
                    "name": name,
                    "last_text": "",
                    "time": "",
                    "count": 0,
                },
            )
            item["count"] += 1
            if not item["last_text"] or m.created_at > timezone.datetime.fromisoformat(
                item.get("time") or "1970-01-01T00:00:00"
            ):
                item["last_text"] = m.text
                item["time"] = m.created_at.isoformat()
            summary[key] = item

        items = []
        for item in summary.values():
            dt = timezone.datetime.fromisoformat(item["time"])
            item["time_display"] = dt.strftime("%H:%M")
            items.append(item)

        total = sum(i["count"] for i in items)
        return JsonResponse({"total": total, "items": items})


class ChatWithUserView(ChatHomeView):
    """
    Abre (ou cria) uma conversa entre o usuário logado e o usuário selecionado.
    """

    def _get_or_create_conversation(self, request: HttpRequest, other_user):
        return get_or_create_conversation_between(request.user, other_user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_model = get_user_model()
        other_user = user_model.objects.get(pk=self.kwargs["user_id"])
        conversation = self._get_or_create_conversation(self.request, other_user)
        context["other_user"] = other_user
        context["active_conversation"] = conversation
        messages_qs = conversation.messages.select_related("sender").all()
        context["messages"] = messages_qs
        last_msg = messages_qs.order_by("-id").first()
        context["last_message_id"] = last_msg.id if last_msg else 0
        chamado_id = self.request.GET.get("chamado")
        context["related_chamado_id"] = chamado_id
        # marcar como lidas mensagens recebidas
        conversation.messages.exclude(sender=self.request.user).filter(
            read_at__isnull=True
        ).update(read_at=timezone.now())
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user_model = get_user_model()
        other_user = user_model.objects.get(pk=self.kwargs["user_id"])
        conversation = self._get_or_create_conversation(request, other_user)
        text = (request.POST.get("text") or "").strip()
        attachment = request.FILES.get("attachment")
        if text or attachment:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text,
                attachment=attachment,
            )
        # Para requisições AJAX (p.ex. colar imagem), evita redirect
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("chat:with_user", user_id=other_user.id)


class ScheduleMeetingView(LoginRequiredMixin, View):
    """
    Tela para agendar uma reunião e enviar o link para participantes via chat.
    """

    template_name = "chat/schedule_meeting.html"

    def _calendar_context(self, request: HttpRequest) -> dict:
        user = self.request.user
        today = timezone.localdate()
        selected_date_str = self.request.GET.get("dia")
        try:
            selected_date = (
                timezone.datetime.fromisoformat(selected_date_str).date()
                if selected_date_str
                else today
            )
        except Exception:
            selected_date = today

        # intervalo do mês para montar calendário
        year = int(self.request.GET.get("year", selected_date.year))
        month = int(self.request.GET.get("month", selected_date.month))

        first_of_month = timezone.datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        last_of_month = timezone.datetime(year, month, last_day, 23, 59, 59)

        month_start = timezone.make_aware(first_of_month)
        month_end = timezone.make_aware(last_of_month)

        month_meetings = (
            Meeting.objects.filter(
                Q(organizer=user) | Q(participants=user),
                status=Meeting.Status.ACTIVE,
            )
            .filter(scheduled_for__gte=month_start, scheduled_for__lte=month_end)
        )

        # mapa dia -> bool se tem reunião
        meetings_by_date = {}
        for m in month_meetings:
            if not m.scheduled_for:
                continue
            local_dt = timezone.localtime(m.scheduled_for)
            d = local_dt.date()
            meetings_by_date[d] = True

        cal = calendar.Calendar(firstweekday=0)
        month_weeks = []
        for week in cal.monthdatescalendar(year, month):
            days = []
            for d in week:
                days.append(
                    {
                        "date": d,
                        "in_month": d.month == month,
                        "has_meetings": meetings_by_date.get(d, False),
                    }
                )
            month_weeks.append(days)

        # reuniões do dia selecionado
        day_start = timezone.make_aware(
            timezone.datetime.combine(selected_date, timezone.datetime.min.time())
        )
        day_end = timezone.make_aware(
            timezone.datetime.combine(selected_date, timezone.datetime.max.time())
        )

        day_meetings = (
            Meeting.objects.filter(
                Q(organizer=user) | Q(participants=user), status=Meeting.Status.ACTIVE
            )
            .filter(scheduled_for__gte=day_start, scheduled_for__lte=day_end)
            .select_related("organizer")
            .prefetch_related("participants")
            .order_by("scheduled_for", "created_at")
        )

        # navegação de mês anterior/próximo
        prev_month = month - 1 or 12
        prev_year = year - 1 if month == 1 else year
        next_month = month + 1 if month < 12 else 1
        next_year = year + 1 if month == 12 else year

        return {
            "selected_date": selected_date,
            "meetings": day_meetings,
            "month_weeks": month_weeks,
            "month": month,
            "year": year,
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
            "today": today,
        }

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = ScheduleMeetingForm(request_user=request.user)
        context = {"form": form}
        context.update(self._calendar_context(request))
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = ScheduleMeetingForm(request.POST, request_user=request.user)
        if not form.is_valid():
            print("ScheduleMeetingView form_invalid errors:", form.errors)
            context = {"form": form}
            context.update(self._calendar_context(request))
            return render(request, self.template_name, context)

        print("ScheduleMeetingView form_valid data:", form.cleaned_data)
        before = Meeting.objects.count()
        user = request.user
        participantes = form.cleaned_data["participantes"]
        externos = form.cleaned_data.get("convidados_externos") or ""
        titulo = form.cleaned_data["titulo"]
        quando = form.cleaned_data.get("quando")

        # Se data/hora não for informada, usar o dia selecionado no calendário (ou hoje) às 09:00
        if not quando:
            today = timezone.localdate()
            selected_date_str = request.GET.get("dia")
            try:
                selected_date = (
                    datetime.fromisoformat(selected_date_str).date()
                    if selected_date_str
                    else today
                )
            except Exception:
                selected_date = today
            naive = datetime.combine(selected_date, dtime(hour=9, minute=0))
            quando = timezone.make_aware(naive)

        room_name = f"meeting-{user.id}-{int(time.time())}"
        meeting_url = f"{settings.MEETING_BASE_URL.rstrip('/')}/{room_name}"

        if quando:
            quando_local = timezone.localtime(quando)
            quando_str = quando_local.strftime("%d/%m/%Y %H:%M")
        else:
            quando_str = "a combinar"

        texto = (
            f"{user.get_username()} agendou uma reunião.\n"
            f"Título: {titulo}\n"
            f"Quando: {quando_str}\n"
            f"Link: {meeting_url}"
        )

        meeting = Meeting.objects.create(
            organizer=user,
            title=titulo,
            scheduled_for=quando,
            room_name=room_name,
        )
        if participantes:
            meeting.participants.set(participantes)

        for outro in participantes:
            conv = get_or_create_conversation_between(user, outro)
            Message.objects.create(conversation=conv, sender=user, text=texto)

        # enviar convites por e-mail com evento de calendário (ICS)
        try:
            self._send_meeting_invites(meeting, participantes, externos)
        except Exception as e:
            print("Erro ao enviar convites de reunião:", repr(e))

        after = Meeting.objects.count()
        print("ScheduleMeetingView created meeting id:", meeting.pk, "count before/after:", before, after)

        return redirect("chat:schedule_meeting")

    def _send_meeting_invites(self, meeting: Meeting, participantes, externos: str):
        import re

        emails = [
            u.email
            for u in participantes
            if getattr(u, "email", "") and "@" in u.email
        ]
        # convidados externos: separados por vírgula ou ponto e vírgula
        if externos:
            for raw in re.split(r"[;,]", externos):
                e = (raw or "").strip()
                if e and "@" in e:
                    emails.append(e)
        # remover duplicados mantendo ordem
        seen = set()
        emails = [e for e in emails if not (e in seen or seen.add(e))]
        if not emails:
            return

        organizer = meeting.organizer
        subject = f"Convite para reunião: {meeting.title}"
        meeting_url = f"{settings.MEETING_BASE_URL.rstrip('/')}/{meeting.room_name}"

        if meeting.scheduled_for:
            local_dt = timezone.localtime(meeting.scheduled_for)
            when_str = local_dt.strftime("%d/%m/%Y %H:%M")
        else:
            when_str = "a combinar"

        body = (
            f"Você foi convidado para uma reunião.\n\n"
            f"Título: {meeting.title}\n"
            f"Organizador: {organizer.get_username()}\n"
            f"Quando: {when_str}\n"
            f"Link da reunião: {meeting_url}\n\n"
            f"Esta reunião também pode ser adicionada ao seu calendário através do anexo ICS."
        )

        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or None,
            to=emails,
        )

        if meeting.scheduled_for:
            # gerar arquivo ICS simples para integração com Outlook/Google/etc.
            start_utc = meeting.scheduled_for.astimezone(dt_timezone.utc)
            end_utc = start_utc + timedelta(minutes=30)
            dt_format = "%Y%m%dT%H%M%SZ"
            uid = f"{meeting.pk}@example.com"
            ics_lines = [
                "BEGIN:VCALENDAR",
                "PRODID:-//Kuttner//Chat Interno//PT-BR",
                "VERSION:2.0",
                "CALSCALE:GREGORIAN",
                "METHOD:REQUEST",
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{timezone.now().astimezone(dt_timezone.utc).strftime(dt_format)}",
                f"DTSTART:{start_utc.strftime(dt_format)}",
                f"DTEND:{end_utc.strftime(dt_format)}",
                f"SUMMARY:{meeting.title}",
                f"DESCRIPTION:Reunião via Comunicação Interna. Link: {meeting_url}",
                f"URL:{meeting_url}",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
            ics_content = "\r\n".join(ics_lines)
            msg.attach(filename="reuniao.ics", content=ics_content, mimetype="text/calendar")

        print("Enviando e-mail de convite para:", emails)
        msg.send(fail_silently=False)
        print("E-mail de convite enviado com sucesso.")


class CancelMeetingView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        meeting = Meeting.objects.filter(pk=pk).first()
        if meeting and meeting.organizer_id == request.user.id:
            meeting.status = Meeting.Status.CANCELLED
            meeting.save(update_fields=["status"])
        return redirect("chat:schedule_meeting")


class EditMeetingView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        meeting = Meeting.objects.filter(pk=pk, organizer=request.user).first()
        if not meeting:
            return redirect("chat:schedule_meeting")

        titulo = (request.POST.get("titulo") or "").strip()
        quando_str = (request.POST.get("quando") or "").strip()
        if titulo:
            meeting.title = titulo
        if quando_str:
            try:
                naive = timezone.datetime.fromisoformat(quando_str)
                meeting.scheduled_for = timezone.make_aware(naive)
            except Exception:
                pass
        meeting.save()
        return redirect("chat:schedule_meeting")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        print("ScheduleMeetingView form_valid data:", form.cleaned_data)
        before = Meeting.objects.count()
        user = self.request.user
        participantes = form.cleaned_data["participantes"]
        externos = form.cleaned_data.get("convidados_externos") or ""
        titulo = form.cleaned_data["titulo"]
        quando = form.cleaned_data.get("quando")

        # Se data/hora não for informada, usar o dia selecionado no calendário (ou hoje) às 09:00
        if not quando:
            today = timezone.localdate()
            selected_date_str = self.request.GET.get("dia")
            try:
                selected_date = (
                    datetime.fromisoformat(selected_date_str).date()
                    if selected_date_str
                    else today
                )
            except Exception:
                selected_date = today
            naive = datetime.combine(selected_date, dtime(hour=9, minute=0))
            quando = timezone.make_aware(naive)

        room_name = f"meeting-{user.id}-{int(time.time())}"
        meeting_url = f"{settings.MEETING_BASE_URL.rstrip('/')}/{room_name}"

        if quando:
            quando_local = timezone.localtime(quando)
            quando_str = quando_local.strftime("%d/%m/%Y %H:%M")
        else:
            quando_str = "a combinar"

        texto = (
            f"{user.get_username()} agendou uma reunião.\n"
            f"Título: {titulo}\n"
            f"Quando: {quando_str}\n"
            f"Link: {meeting_url}"
        )

        meeting_id = self.request.POST.get("meeting_id")
        if meeting_id:
            meeting = Meeting.objects.filter(pk=meeting_id, organizer=user).first()
            if meeting:
                meeting.title = titulo or meeting.title
                meeting.scheduled_for = quando or meeting.scheduled_for
                meeting.save()
            else:
                meeting = Meeting.objects.create(
                    organizer=user,
                    title=titulo,
                    scheduled_for=quando,
                    room_name=room_name,
                )
        else:
            meeting = Meeting.objects.create(
                organizer=user,
                title=titulo,
                scheduled_for=quando,
                room_name=room_name,
            )
        after = Meeting.objects.count()
        print("ScheduleMeetingView created meeting id:", meeting.pk, "count before/after:", before, after)
        if participantes:
            meeting.participants.set(participantes)

        for outro in participantes:
            conv = get_or_create_conversation_between(user, outro)
            Message.objects.create(conversation=conv, sender=user, text=texto)

        # enviar convites por e-mail com evento de calendário (ICS)
        try:
            self._send_meeting_invites(meeting, participantes, externos)
        except Exception:
            # não quebrar o fluxo se o envio de e-mail falhar
            pass

        return super().form_valid(form)

    def _send_meeting_invites(self, meeting: Meeting, participantes, externos: str):
        import re

        emails = [
            u.email
            for u in participantes
            if getattr(u, "email", "") and "@" in u.email
        ]
        # convidados externos: separados por vírgula ou ponto e vírgula
        if externos:
            for raw in re.split(r"[;,]", externos):
                e = (raw or "").strip()
                if e and "@" in e:
                    emails.append(e)
        # remover duplicados mantendo ordem
        seen = set()
        emails = [e for e in emails if not (e in seen or seen.add(e))]
        if not emails:
            return

        organizer = meeting.organizer
        subject = f"Convite para reunião: {meeting.title}"
        meeting_url = f"{settings.MEETING_BASE_URL.rstrip('/')}/{meeting.room_name}"

        if meeting.scheduled_for:
            local_dt = timezone.localtime(meeting.scheduled_for)
            when_str = local_dt.strftime("%d/%m/%Y %H:%M")
        else:
            when_str = "a combinar"

        body = (
            f"Você foi convidado para uma reunião.\n\n"
            f"Título: {meeting.title}\n"
            f"Organizador: {organizer.get_username()}\n"
            f"Quando: {when_str}\n"
            f"Link da reunião: {meeting_url}\n\n"
            f"Esta reunião também pode ser adicionada ao seu calendário através do anexo ICS."
        )

class MeetNowView(LoginRequiredMixin, View):
    """
    Gera uma sala instantânea no Jitsi e redireciona o usuário.
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = request.user
        room_name = f"meet-now-{user.id}-{int(time.time())}"
        meeting_url = f"{settings.MEETING_BASE_URL.rstrip('/')}/{room_name}"
        # Se for chamada via AJAX, retornamos apenas a URL para ser usada em um iframe/modal.
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"room_url": meeting_url})
        # Fallback: navegação normal abre em nova aba/janela.
        return redirect(meeting_url)

