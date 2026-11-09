import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from server.network.client_handler import handle_client


logger = logging.getLogger(__name__)


class TCPServer:
    """Многопоточный TCP-сервер."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5050,
        max_workers: int = 10,
    ) -> None:
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self._stop_event = Event()

    def serve_forever(self) -> None:
        """Запускает сервер и принимает подключения."""

        with ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="client",
        ) as executor:

            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            ) as server_socket:

                server_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_REUSEADDR,
                    1,
                )

                server_socket.bind((self.host, self.port))
                server_socket.listen()
                server_socket.settimeout(0.5)

                logger.info(
                    "TCP-сервер запущен: %s:%s",
                    self.host,
                    self.port,
                )

                try:
                    while not self._stop_event.is_set():
                        try:
                            client_socket, client_address = (
                                server_socket.accept()
                            )

                        except socket.timeout:
                            continue

                        except OSError:
                            if self._stop_event.is_set():
                                break
                            raise

                        executor.submit(
                            handle_client,
                            client_socket,
                            client_address,
                        )

                finally:
                    logger.info("Остановка TCP-сервера.")

    def stop(self) -> None:
        """Запрашивает остановку сервера."""

        self._stop_event.set()
