import socket
import sys
import signal


def enviar_linea(sock: socket.socket, mensaje: str):
    """Envía un mensaje UTF-8 terminado en salto de línea."""
    try:
        sock.sendall((mensaje + "\n").encode("utf-8"))
    except Exception:
        pass


def recibir_linea(sock: socket.socket, buffer: bytes):
    """Recibe datos del socket acumulando hasta completar una línea."""
    while b"\n" not in buffer:
        chunk = sock.recv(1024)

        if not chunk:
            if buffer:
                mensaje = buffer.decode("utf-8").strip()
                return mensaje, b""
            return None, b""

        buffer += chunk

    linea, buffer = buffer.split(b"\n", 1)
    return linea.decode("utf-8").strip(), buffer


def main():
    # Comprobar argumentos exigidos: identificador, ip del servidor y puerto
    if len(sys.argv) != 4:
        print("Uso: python3 aerogenerador.py <identificador> <ip_servidor> <puerto>")
        sys.exit(1)

    identificador = sys.argv[1]
    ip_servidor = sys.argv[2]
    puerto = int(sys.argv[3])

    # 1. Crear socket TCP/IP (AF_INET, SOCK_STREAM)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 2. Conectar con el servidor (IP + puerto)
        s.connect((ip_servidor, puerto))
    except Exception as e:
        print(f"No se pudo conectar con el servidor: {e}")
        s.close()
        sys.exit(1)

     # Crear un flujo de lectura que conserva los mensajes pendientes
    buffer = b""
    # Enviar mensaje de identificación inicial al servidor
    enviar_linea(s, f"CONECTAR {identificador}")

    # Recibir respuesta del servidor (ACEPTADO / RECHAZADO)
    respuesta, buffer = recibir_linea(s, buffer)
    if not respuesta.startswith("ACEPTADO"):
        print(f"Conexión rechazada: {respuesta}")
        s.close()
        sys.exit(1)

    print(f"Conectado al centro de control como {identificador}.")
    print("Esperando órdenes... (Ctrl+C para desconectar)")

    # Manejo de Ctrl+C para desconexión limpia y ordenada
    def salir(sig, frame):
        print("\nDesconectando del centro de control...")
        enviar_linea(s, "DESCONECTAR")
        s.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, salir)

    # 3. Comunicación continua (recibir órdenes o avisos del servidor)
    try:
        while True:
            msg, buffer = recibir_linea(s, buffer)
            if not msg:
                print("El servidor ha cerrado la comunicación.")
                break

            if msg.startswith("ORDEN "):
                orden = msg.split(" ", 1)[1]
                print(f"ORDEN RECIBIDA: {orden}")
                # Confirmar la orden de vuelta al servidor
                enviar_linea(s, f"CONFIRMADO {orden}")
                print("Confirmación enviada al centro de control.")
            elif msg.startswith("AVISO "):
                print(f"AVISO DEL CENTRO DE CONTROL: {msg.split(' ', 1)[1]}")
            elif msg == "SERVIDOR_CIERRA":
                print("El centro de control se ha cerrado.")
                break
    except Exception:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    main()