import requests
import hashlib
import json
from time import time
from textwrap import dedent
from urllib import response
from urllib.parse import urlparse
from uuid import uuid4
from crypt import methods
from flask import Flask, jsonify, request



class Blockchain(object):
    def __init__(self) -> None:
        # Um chain contém vários blocos
        self.chain = []
        self.transacoes_atuais = []
        self.nodes = set()

        # Cria um bloco de gênese
        self.novo_bloco(hash_anterior=1, prova=100)

    def novo_bloco(self, prova, hash_anterior=None) -> dict:
        """
        Cria um novo Bloco e adiciona ele no Blockchain
        :param prova: <int> A prova dada pelo algoritmo Proof of Work
        :param hash_anterior: (Opcional) <str> Hash do bloco anterior
        :param return: <dict> Novo bloco
        """

        # Um bloco tem a estrutura abaixo
        bloco = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transacoes': self.transacoes_atuais,
            'prova': prova,
            'hash_anterior': hash_anterior or self.hash(self.chain[-1]),
        }

        # Reseta a lista atual de transacoes
        self.transacoes_atuais = []

        self.chain.append(bloco)
        return bloco

    def nova_transacao(self, sender, recipiente, quantidade) -> int:
        """
        Adiciona uma nova transação para ir para o próximo bloco minerado
        :param sender: <str> Endereço do Sender
        :param recipiente: <str> Endereço do Recipiente
        :param quantidade: <int> Quantidade
        :para return: <int> O índice do bloco que irá realizar esta transação
        """

        self.transacoes_atuais.append({
            'sender': sender,
            'recipiente': recipiente,
            'quantidade': quantidade,
        })

        return self.ultimo_bloco['index'] + 1

    @staticmethod
    def hash(bloco) -> str:
        """
        Cria um hash SHA-256 de um bloco
        :param bloco: <dict> Bloco
        :return: <str>
        """
        # Devemos ter certeza de que o dicionário está ordenado, ou teremos hashes inconsistentes
        string_bloco = json.dumps(bloco, sort_keys=True).encode()
        return hashlib.sha256(string_bloco).hexdigest()

    @property
    def ultimo_bloco(self):
        # Retorna o último bloco na chain
        return self.chain[-1]

    def prova_de_trabalho(self, ultima_prova) -> int:
        """
        Algoritmo simples de Prova de Trabalho
        - Encontrar um numero p' de tal modo que hash(p*p') contém 4 zeros à esquerda, onde p é anterior a p'
        - p é a prova anterior e p' é a nova prova
        :param ultima_prova: <int>
        :return: <int>
        """
        prova = 0
        while self.prova_valida(ultima_prova, prova) is False:
            prova += 1

        return prova

    @staticmethod
    def prova_valida(ultima_prova, prova) -> bool:
        """
        Valida a prova: O hash(ultima_prova, prova) contém 4 zeros à esquerda?
        :param ultima_prova: <int> Prova anterior
        :param prova: <int> Prova atual
        :return: <bool> True se correto, Falso se não é
        """
        hipotese = f'{ultima_prova}{prova}'.encode()
        hipotese_hash = hashlib.sha256(hipotese).hexdigest()
        return hipotese_hash[:4] == '0000'

    def registrar_node(self, endereco):
        """
        Adiciona um novo node para a lista de nodes
        :param endereco: <str> Endereco de um node. Ex. 'http://192.168.0.5:5000'
        :return: None
        """
        parsed_url = urlparse(endereco)
        self.nodes.add(parsed_url.netloc)
    
    def chain_valido(self, chain) -> bool:
        """
        Determina se o blockchain é válido
        :param chain: <list> Um blockchain
        :return: <bool> True se válido, Falso se não
        """
        ultimo_bloco = chain[0]
        indice_atual = 1

        while indice_atual < len(chain):
            bloco = chain[indice_atual]
            print(f'{ultimo_bloco}')
            print(f'{bloco}')
            print('\n-------------\n')

            # Checa que o hash do bloco está correto
            if bloco['hash_anterior'] != self.hash(ultimo_bloco):
                return False

            # Checa se a prova de trabalho está correta
            if not self.prova_valida(ultimo_bloco['prova'], bloco['prova']):
                return False

            ultimo_bloco = bloco
            indice_atual += 1
        
        return True

    def resolver_conflitos(self):
        """
        Isto é um algoritmo de consenso. Ele resolve conflitos
        substituindo nossa chain com o maior da rede.
        :return: <bool> True se nossa chain foi substituída, False se não
        """
        vizinhos = self.nodes
        novo_chain = None

        # Estamos somente verificando por chains maiores que os nossos
        tamanho_maximo = len(self.chain)

        # Pegue e verifique as cadeias de todos os nós em nossa rede
        for node in vizinhos:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                tamanho = response.json()['tamanho']
                chain = response.json()['chain']

                # Verifica se o tamanho é longo e o chain é valido
                if tamanho > tamanho_maximo and self.chain_valido(chain):
                    tamanho_maximo = tamanho
                    novo_chain = chain
        
        # Troque nosso chain se nos descobrimos um novo, chain válido maior que os nossos
        if novo_chain:
            self.chain = novo_chain
            return True
        
        return False

# Instanciar nosso Node
app = Flask(__name__)

# Gerar um endereço global único para este node
node_identificador = str(uuid4()).replace('-','')

# Instanciar o Blockchain
blockchain = Blockchain()

@app.route('/minerar', methods=['GET'])
def mine():
    # Executamos o algoritmo de prova de trabalho para obter a próxima prova...
    ultimo_bloco = blockchain.ultimo_bloco
    ultima_prova = blockchain.ultimo_bloco['prova']
    prova = blockchain.prova_de_trabalho(ultima_prova)

    # Devemos receber uma recompensa por encontrar a prova. 
    # O remetente é "0" para significar que este nó extraiu uma nova moeda.
    blockchain.nova_transacao(
        sender='0',
        recipiente=node_identificador,
        quantidade=1,
    )

    # Forja o novo bloco adicionando-o à cadeia
    hash_anterior = blockchain.hash(ultimo_bloco)
    bloco = blockchain.novo_bloco(prova, hash_anterior)

    response = {
        'message': 'Novo bloco forjado',
        'index': bloco['index'],
        'transacoes': bloco['transacoes'],
        'prova': bloco['prova'],
        'hash_anterior': bloco['hash_anterior'],
    }
    return jsonify(response), 200

@app.route('/transacoes/novo', methods=['POST'])
def nova_transacao():
    valores = request.get_json()

    # Verificar que os campos requeridos são os dados enviados pelo POST
    requeridos = ['sender', 'recipiente', 'quantidade']
    if not all(k in valores for k in requeridos):
        return 'Valores faltando', 400 

    # Criar uma nova transação
    indice = blockchain.nova_transacao(valores['sender'], valores['recipiente'], valores['quantidade'])
    response = {'message': f'Transação será adicionada ao bloco {indice}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'tamanho': len(blockchain.chain),
    }
    return jsonify(response)

@app.route('/nodes/register', methods=['POST'])
def registrar_nodes():
    valores = request.get_json()

    nodes = valores.get('nodes')
    if nodes is None:
        return 'Erro: por favor, forneça uma lista válida de nodes'

    for node in nodes:
        blockchain.registrar_node(node)

    response = {
        'message': 'Novos nodes foram adicionados',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consenso():
    substituido = blockchain.resolver_conflitos()

    if substituido:
        response = {
            'message': 'Nosso chain foi substituído',
            'novo_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Nosso chain é autoritativo',
            'novo_chain': blockchain.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)