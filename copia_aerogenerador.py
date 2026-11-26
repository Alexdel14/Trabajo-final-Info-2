import socket
import sys

def enviar_linea(sock: socket.socket, mensaje: str):
    """Envía un mensaje UTF-8 terminado en salto de línea."""
    try:
        sock.sendall((mensaje + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def recibir_linea(sock: socket.socket, buffer: bytes):
    """Recibe datos acumulando hasta completar una línea."""
    while b"\n" not in buffer:
        try:
            chunk = sock.recv(1024)

        except socket.timeout:
            continue

        if not chunk:
            if buffer:
                mensaje = buffer.decode("utf-8").strip()
                return mensaje, b""
            return None, b""

        buffer += chunk

    linea, buffer = buffer.split(b"\n", 1)
    return linea.decode("utf-8").strip(), buffer


def main():
    # Comprobar los argumentos
    if len(sys.argv) != 4:
        print(
            "Uso: python3 aerogenerador.py "
            "<identificador> <ip_servidor> <puerto>"
        )
        sys.exit(1)

    identificador = sys.argv[1]
    ip_servidor = sys.argv[2]

    try:
        puerto = int(sys.argv[3])
    except ValueError:
        print("El puerto debe ser un número entero.")
        sys.exit(1)

    # Crear el socket TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Conectar con el servidor
        s.connect((ip_servidor, puerto))

        s.settimeout(0.5)

    except OSError as e:
        print(f"No se pudo conectar con el servidor: {e}")
        s.close()
        sys.exit(1)

    buffer = b""

    try:
        # Identificarse ante el servidor
        if not enviar_linea(s, f"CONECTAR {identificador}"):
            print("No se pudo enviar la identificación.")
            return

        respuesta, buffer = recibir_linea(s, buffer)

        if respuesta is None or not respuesta.startswith("ACEPTADO"):
            print(f"Conexión rechazada: {respuesta}")
            return

        print(f"Conectado al centro de control como {identificador}.")
        print("Esperando órdenes... (Ctrl+C para desconectar)")

        # Comunicación continua con el servidor
        while True:
            msg, buffer = recibir_linea(s, buffer)

            if msg is None:
                print("El servidor ha cerrado la comunicación.")
                break

            if msg.startswith("ORDEN "):
                orden = msg.split(" ", 1)[1]

                print(f"ORDEN RECIBIDA: {orden}")

                # Confirmar la orden
                if enviar_linea(s, f"CONFIRMADO {orden}"):
                    print("Confirmación enviada al centro de control.")
                else:
                    print("No se pudo enviar la confirmación.")
                    break

            elif msg.startswith("AVISO "):
                print(
                    "AVISO DEL CENTRO DE CONTROL: "
                    f"{msg.split(' ', 1)[1]}"
                )

            elif msg == "SERVIDOR_CIERRA":
                print("El centro de control se ha cerrado.")
                break

    except KeyboardInterrupt:
        print("\nDesconectando del centro de control...")

        enviar_linea(s, "DESCONECTAR")

        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

       

        print(f"{identificador} se ha desconectado correctamente.")

    finally:
        s.close()

if __name__ == "__main__":
    main()
