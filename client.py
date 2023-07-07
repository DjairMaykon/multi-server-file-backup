import socket
import os

class Cliente:
    def __init__(self, proxy_host, proxy_port):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.recover_folder = f"{os.path.abspath(os.getcwd())}/recover_files"

    def conectar_proxy(self):
        self.proxy_socket.connect((self.proxy_host, self.proxy_port))

    def desconectar_proxy(self):
        self.proxy_socket.close()

    def enviar_requisicao(self, requisicao):
        self.proxy_socket.sendall(requisicao)

    def receber_resposta(self):
        resposta = self.proxy_socket.recv(1024)
        return resposta

    def depositar_arquivo(self):
        nome_arquivo = input("Digite o nome do arquivo: ")
        tolerancia = input("Digite a tolerância: ")

        requisicao = f"D#{nome_arquivo}#{tolerancia}"
        self.enviar_requisicao(requisicao.encode('utf-8'))
        resposta = self.receber_resposta()
        print(f"Proxy: {resposta.decode()}")

        with open(nome_arquivo, 'rb') as arquivo:
            while True:
                arquivo_bytes = arquivo.read(1024)
                if not arquivo_bytes:
                    break
                self.enviar_requisicao(arquivo_bytes)
        self.enviar_requisicao('\x00'.encode())
        resposta = self.receber_resposta()
        print(f"Proxy: {resposta.decode()}")


    def mudar_tolerancia(self):
        nome_arquivo = input("Digite o nome do arquivo: ")
        nova_tolerancia = input("Digite a nova tolerância: ")
        requisicao = f"M#{nome_arquivo}#{nova_tolerancia}"
        self.enviar_requisicao(requisicao.encode('utf-8'))

        resposta = self.receber_resposta()
        print(resposta)

    def recuperar_arquivo(self):
        if not os.path.exists(self.recover_folder):
            os.makedirs(self.recover_folder)

        requisicao = f"L"
        self.enviar_requisicao(requisicao.encode('utf-8'))
        resposta = self.receber_resposta()
        print(f"Arquivos depositados pelo proxy: {resposta.decode()}")

        nome_arquivo = input("Digite o nome do arquivo: ")
        requisicao = f"R#{nome_arquivo}"
        self.enviar_requisicao(requisicao.encode())

        with open(f"{self.recover_folder}/{nome_arquivo}", 'wb') as arquivo:
            while True:
                resposta = self.receber_resposta()
                if not resposta:
                    break
                arquivo.write(resposta)
        print(f"Arquivo '{nome_arquivo}' recuperado com sucesso")
        # else:
        #     print(f"Arquivo '{nome_arquivo}' não encontrado")

    def menu(self):
        while True:
            print("1. Depositar arquivo")
            print("2. Mudar tolerância de arquivo")
            print("3. Recuperar arquivo")
            print("4. Sair")

            opcao = input("Digite o número da opção desejada: ")

            if opcao == '1':
                self.depositar_arquivo()
            elif opcao == '2':
                self.mudar_tolerancia()
            elif opcao == '3':
                self.recuperar_arquivo()
            elif opcao == '4':
                break
            else:
                print("Opção inválida. Tente novamente.")

if __name__ == '__main__':
    proxy_host = input("Digite o host do proxy: ")
    proxy_port = int(input("Digite a porta do proxy: "))

    cliente = Cliente(proxy_host, proxy_port)
    cliente.conectar_proxy()
    cliente.menu()
    cliente.desconectar_proxy()
