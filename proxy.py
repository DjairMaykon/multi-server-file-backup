import os
import socket
import threading
import random

from server import Server

class Proxy:
    def __init__(self):
        self.host = 'localhost'
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, 0))
        self.port = self._socket.getsockname()[1]

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.servers = {}  # Dicionário para armazenar informações dos servidores
        self.arquivos = {}  # Dicionário para armazenar a localização dos arquivos

    def start_server(self, num_servers):
        for i in range(num_servers):
            server = Server(len(self.servers) + 1)
            server_thread = threading.Thread(target=server.start)
            server_thread.start()
            self.servers[server.server_id] = server
            print(f"[PROXY] Servidor {server.server_id} iniciado em {server.host}:{server.port}\n")

    def connect_server(self, server_id):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.connect((self.servers[server_id].host, self.servers[server_id].port))

    def desconnect_server(self):
        self._server_socket.close()
    def send_request_server(self, data):
        self._server_socket.sendall(data)

    def receive_response_server(self):
        resposta = self._server_socket.recv(1024)
        return resposta

    def handle_depositar(self, conn, nome_arquivo, arquivo_bytes, tolerancia):
        # Verificar se o arquivo existe no proxy
        if nome_arquivo in self.arquivos:
            conn.sendall(f"Arquivo {nome_arquivo} já foi depositado".encode('utf-8'))
            return

        arquivo_bytes = self.receber_arquivo(conn)

        # Verificar se é necessário criar mais servidores
        num_servers = len(self.servers)
        if num_servers < tolerancia:
            self.start_server(tolerancia - num_servers)

        # Seleciona servidores aleatorios conforme tolerancia
        server_ids = list(self.servers.keys())
        selected_servers = random.sample(server_ids, tolerancia)

        # Salvar o arquivo nos servidores selecionados
        for server_id in selected_servers:
            self.connect_server(server_id)

            request = f"D#{nome_arquivo}"
            self.send_request_server(request.encode('utf-8'))
            print(f"[PROXY] Request servidor {server_id}: {request}")
            resposta = self.receive_response_server()
            print(f"[PROXY] Resposta servidor {server_id}: {resposta}")

            start_index = 0
            while start_index < len(arquivo_bytes):
                end_index = start_index + 1024
                chunk = arquivo_bytes[start_index:end_index]
                self.send_request_server(chunk)
                start_index = end_index

            self.desconnect_server()

        # Armazenar os servidores onde o arquivo foi depositado
        self.arquivos[nome_arquivo] = selected_servers

    def handle_mudar_tolerancia(self, conn, nome_arquivo, nova_tolerancia):
        # Verificar se o arquivo existe no proxy
        if nome_arquivo not in self.arquivos:
            response = "Arquivo não encontrado no proxy"
            conn.sendall(response.encode('utf-8'))
            return

        # Obter os servidores onde o arquivo está armazenado atualmente
        servidores_arquivo = self.arquivos[nome_arquivo]
        
        # Verificar se é necessário criar mais servidores
        server_ids = list(self.servers.keys())
        num_servers = len(server_ids)
        if num_servers < nova_tolerancia:
            self.start_server(nova_tolerancia - num_servers)
            server_ids = list(self.servers.keys())

        # Atualizar a tolerância do arquivo
        if nova_tolerancia < len(servidores_arquivo):
            # Remover arquivos de servidores aleatórios
            servidores_remover = random.sample(servidores_arquivo, len(servidores_arquivo) - nova_tolerancia)
            for server_id in servidores_remover:
                self.connect_server(server_id)
                self.send_request_server(f"E#{nome_arquivo}".encode('utf-8'))
                resposta = self.receive_response_server()
                print(f"[PROXY] Resposta servidor {server_id}: {resposta}")
                self.desconnect_server()

                # Remover servidor da lista de servidores do arquivo
                self.arquivos[nome_arquivo].remove(server_id)
        elif nova_tolerancia > len(servidores_arquivo):
            arquivo_bytes = b''
            arquivo_server_id = self.arquivos[nome_arquivo][0]
            self.connect_server(arquivo_server_id)
            self.send_request_server(f"R#{nome_arquivo}".encode('utf-8'))
            resposta = self.receive_response_server()
            print(f"[PROXY] Resposta servidor {arquivo_server_id}: {resposta}")
            while True:
                received_data = self.receive_response_server()
                if not received_data:
                    break
                arquivo_bytes += received_data
            self.desconnect_server()
            # Adicionar arquivos em servidores disponíveis
            servidores_disponiveis = set(server_ids) - servidores_arquivo
            servidores_adicionar = random.sample(servidores_disponiveis, nova_tolerancia - len(servidores_arquivo))
            for server_id in servidores_adicionar:
                self.connect_server(server_id)
                self.send_request_server(f"D#{nome_arquivo}".encode('utf-8'))
                resposta = self.receive_response_server()
                print(f"[PROXY] Resposta servidor {server_id}: {resposta}")
                start_index = 0
                while start_index < len(arquivo_bytes):
                    end_index = start_index + 1024
                    chunk = arquivo_bytes[start_index:end_index]
                    self.send_request_server(chunk)
                    start_index = end_index
                self.desconnect_server()

                # Adicionar servidor à lista de servidores do arquivo
                self.arquivos[nome_arquivo].add(server_id)

        # Enviar uma resposta de sucesso ao cliente
        response = "Tolerância alterada com sucesso"
        conn.sendall(response.encode('utf-8'))

    def handle_recuperar(self, conn, nome_arquivo):
        # Verificar se o arquivo existe no proxy
        if nome_arquivo not in self.arquivos.keys():
            response = "Arquivo não encontrado no proxy"
            conn.sendall(response.encode('utf-8'))
            return

        # Recuperar o arquivo de servidor aleatorio
        server_id = random.choice(self.arquivos[nome_arquivo])
        self.connect_server(server_id)
        self.send_request_server(f"R#{nome_arquivo}".encode('utf-8'))
        resposta = self.receive_response_server()
        print(f"[PROXY] Resposta servidor {server_id}: {resposta}")
        while True:
            received_data = self.receive_response_server()
            if not received_data:
                break
            conn.sendall(received_data)
        self.desconnect_server()

        # Enviar uma resposta de sucesso ao cliente
        response = "Arquivo recuperado com sucesso"
        conn.sendall(response.encode('utf-8'))

    def handle_listar(self, conn):
        # Enviar uma resposta de sucesso ao cliente
        response = ", ".join(self.arquivos.keys())
        conn.sendall(response.encode('utf-8'))

    def receber_arquivo(self, conn):
        conn.sendall(str.encode('Iniciando recebimento do arquivo'))
        print(f"[PROXY] Iniciando recebimento do arquivo")
        arquivo_bytes = b''
        while True:
            received_data = conn.recv(1024)
            if not received_data or received_data.decode() == '\x00':
                break
            arquivo_bytes += received_data
        print(f"[PROXY] Finalizando recebimento do arquivo")
        conn.sendall(str.encode('Recebimento do arquivo finalizado'))

        return arquivo_bytes
    def start(self):
        self._socket.listen(1)
        print(f"[PROXY] Proxy ouvindo em {self.host}:{self.port}")

        while True:
            # Aceite a conexão do cliente
            client_conn, client_addr = self._socket.accept()
            print(f"[PROXY] Conexão estabelecida com {client_addr}")

            # Receba a requisição do cliente
            data = client_conn.recv(1024)
            if not data:
                break
            data = data.decode('utf-8')
            print(f"[PROXY] Request: {data}")

            # Separe o tipo de requisição e os dados adicionais
            tipo = data.split('#', 1)[0]

            # Lide com a requisição do cliente
            if tipo == 'D':  # Depositar arquivo
                _, arquivo_nome, tolerancia = data.split('#')
                    self.handle_depositar(client_conn, arquivo_nome, arquivo_bytes, int(tolerancia))
            elif tipo == 'M':  # Mudar tolerância
                _, arquivo_nome, nova_tolerancia = data.split('#')
                self.handle_mudar_tolerancia(client_conn, arquivo_nome, int(nova_tolerancia))
            elif tipo == 'R':  # Recuperar arquivo
                _, arquivo_nome = data
                self.handle_recuperar(client_conn, arquivo_nome)
            elif tipo == 'L':  # Listar arquivos
                self.handle_listar(client_conn)

            # Feche a conexão com o cliente
            client_conn.close()


# Exemplo de uso das classes Proxy e Server
if __name__ == '__main__':
    proxy = Proxy()  # Defina o host e a porta do proxy
    proxy.start_server(3)  # Defina o número inicial de servidores
    proxy.start()