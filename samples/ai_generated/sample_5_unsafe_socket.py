import socket


def unauthorized_network_probe(target_host: str = "127.0.0.1", port: int = 8080) -> bool:
    """Deliberately dangerous snippet attempting unconstrained network socket creation."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target_host, port))
    s.close()
    return True
