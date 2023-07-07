import socket
import os

class Server:
    def __init__(self, server_id):
        self.server_id = server_id

        self.host = 'localhost'
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, 0))
        self.port = self._socket.getsockname()[1]

        self.folder = f"{os.path.abspath(os.getcwd())}/server_{server_id}"
        # Crie a pasta para armazenar os arquivos
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def depositar_arquivo(self, conn, nome_arquivo ):
        conn.sendall('Iniciando deposito'.encode())
        print(f"[SERVER {self.server_id}] Iniciando deposito do arquivo {nome_arquivo}")

        arquivo_path = os.path.join(self.folder, nome_arquivo)
        # Salvar o arquivo no servidor
        with open(arquivo_path, 'wb') as file:
            while True:
                arquivo_bytes = conn.recv(1024)
                if not arquivo_bytes or arquivo_bytes.decode() == '\x00':
                    break
                file.write(arquivo_bytes)

        conn.sendall('Deposito finalizado com sucesso'.encode())
        print(f"[SERVER {self.server_id}] Finalizando deposito do arquivo {nome_arquivo}")

    def excluir_arquivo(self, conn, nome_arquivo):
        arquivo_path = os.path.join(self.folder, nome_arquivo)
        if os.path.exists(arquivo_path):
            os.remove(arquivo_path)
            conn.sendall('Arquivo removido com sucesso.'.encode())
            print(f"[SERVER {self.server_id}] Arquivo '{nome_arquivo}' removido")
        else:
            conn.sendall('Arquivo não está no servidor.'.encode())
            print(f"[SERVER {self.server_id}] Arquivo '{nome_arquivo}' não encontrado no servidor")

    def recuperar_arquivo(self, conn, nome_arquivo):
        arquivo_path = os.path.join(self.folder, nome_arquivo)
        if os.path.exists(arquivo_path):
            conn.sendall('Iniciando recuperação'.encode())

            with open(arquivo_path, 'rb') as file:
                while True:
                    arquivo_bytes = file.read(1024)
                    if not arquivo_bytes:
                        break
                    conn.sendall(arquivo_bytes)
            conn.sendall('\x00'.encode())

            conn.sendall('Recuperação finalizada com sucesso'.encode())
            print(f"[SERVER {self.server_id}] Arquivo '{nome_arquivo}' recuperado")
        else:
            conn.sendall('Arquivo não está no servidor.'.encode())
            print(f"[SERVER {self.server_id}] Arquivo '{nome_arquivo}' não encontrado no servidor")

    def start(self):
        self._socket.listen(1)
        print(f"[SERVER {self.server_id}] Servidor iniciado em {self.host}:{self.port}\n")

        while True:
            # Aceite a conexão do cliente
            conn, addr = self._socket.accept()
            print(f"[SERVER {self.server_id}] Conexão estabelecida com {addr}")

            # Receba a requisição do cliente
            data = conn.recv(1024)
            if not data:
                break
            data = data.decode('utf-8')
            print(f"[SERVER {self.server_id}] Request: {data}")

            # Separe o tipo de requisição e os dados adicionais
            tipo, nome_arquivo = data.split('#', 1)[0]

            # Lidar com a requisição do cliente
            if tipo == 'D':  # Depositar arquivo
                self.depositar_arquivo(conn, nome_arquivo)
            elif tipo == 'E':  # Remover arquivo
                self.excluir_arquivo(conn, nome_arquivo)
            elif tipo == 'R':  # Recuperar arquivo
                self.recuperar_arquivo(conn, nome_arquivo)

            # Fechar a conexão com o cliente
            conn.close()