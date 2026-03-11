from pathlib import Path


def caminho_hd_virtual(user, filename, categoria="chat", obra_id=None, obra_nome=None):
    """
    Implementação simplificada para ambiente de demo/portfólio.
    Armazena arquivos em uma pasta local por usuário e categoria.
    """
    base = Path("media") / "HDvirtual"
    user_part = getattr(user, "username", "anon")
    return str(base / user_part / categoria / filename)

