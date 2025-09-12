#!/usr/bin/env python3
"""
Script para busca avançada na API Pública do DataJud - VERSÃO CORRIGIDA
Permite filtrar por classe, assunto, movimento, data e tribunal
"""

import requests
import json
from datetime import datetime
import urllib3
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Desabilita warnings SSL (se necessário)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DataJudAPI:
    def __init__(self):
        self.api_key = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
        self.base_url = "https://api-publica.datajud.cnj.jus.br"
        
        # Headers corrigidos - alguns problemas podem estar aqui
        self.headers = {
            "Authorization": f"APIKey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DataJud-Client/1.0"
        }
        
        # Mapeamento de tribunais disponíveis
        self.tribunais = {
            "TJSP": "api_publica_tjsp",
            "TJRJ": "api_publica_tjrj",
            "TJMG": "api_publica_tjmg",
            "TJRS": "api_publica_tjrs",
            "TJPR": "api_publica_tjpr",
            "TJSC": "api_publica_tjsc",
            "TJBA": "api_publica_tjba",
            "TJGO": "api_publica_tjgo",
            "TJDF": "api_publica_tjdf",
            "TJPE": "api_publica_tjpe"
        }
    
    def testar_conexao(self, tribunal):
        """Testa a conexão com um endpoint específico"""
        endpoint = self.tribunais[tribunal]
        url = f"{self.base_url}/{endpoint}/_search"
        
        # Query mais simples possível para teste
        query = {
            "size": 1,
            "query": {
                "match_all": {}
            }
        }
        
        try:
            logger.info(f"Testando conexão com: {url}")
            logger.info(f"Headers: {self.headers}")
            logger.info(f"Query: {json.dumps(query, indent=2)}")
            
            response = requests.post(
                url, 
                headers=self.headers, 
                json=query, 
                verify=False, 
                timeout=30
            )
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Response Text: {response.text}")
            
            response.raise_for_status()
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na conexão: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return False, str(e)
    
    def construir_query_simples(self, tamanho=10):
        """Constrói uma query muito simples para teste inicial"""
        return {
            "size": min(tamanho, 10),  # Limita a 10 para teste
            "query": {
                "match_all": {}
            }
        }
    
    def construir_query(self, classe_codigo=None, assunto_codigo=None, movimento_codigo=None, 
                       data_inicio=None, data_fim=None, tamanho=10):
        """Constrói a query Elasticsearch para busca - versão corrigida"""
        
        query = {
            "size": min(tamanho, 100),  # API pode ter limite
            "query": {
                "bool": {
                    "must": []
                }
            }
        }
        
        # Filtros mais robustos
        filtros = []
        
        # Filtro por classe - usando diferentes possíveis campos
        if classe_codigo:
            filtros.append({
                "bool": {
                    "should": [
                        {"term": {"classe.codigo": str(classe_codigo)}},
                        {"term": {"classe.codigo": classe_codigo}},
                        {"match": {"classe.codigo": classe_codigo}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        # Filtro por assunto - versão mais flexível
        if assunto_codigo:
            filtros.append({
                "bool": {
                    "should": [
                        {
                            "nested": {
                                "path": "assuntos",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {"term": {"assuntos.codigo": str(assunto_codigo)}},
                                            {"term": {"assuntos.codigo": assunto_codigo}}
                                        ]
                                    }
                                }
                            }
                        },
                        {"term": {"assunto.codigo": str(assunto_codigo)}},
                        {"term": {"assunto.codigo": assunto_codigo}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        # Filtro por movimento - versão mais flexível
        if movimento_codigo:
            filtros.append({
                "bool": {
                    "should": [
                        {
                            "nested": {
                                "path": "movimentos",
                                "query": {
                                    "bool": {
                                        "should": [
                                            {"term": {"movimentos.codigo": str(movimento_codigo)}},
                                            {"term": {"movimentos.codigo": movimento_codigo}}
                                        ]
                                    }
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            })
        
        # Filtro por intervalo de datas - campos possíveis
        if data_inicio or data_fim:
            date_range = {}
            if data_inicio:
                date_range["gte"] = data_inicio
            if data_fim:
                date_range["lte"] = data_fim
            
            # Tenta diferentes campos de data que podem existir
            filtros.append({
                "bool": {
                    "should": [
                        {"range": {"dataAjuizamento": date_range}},
                        {"range": {"dataHoraUltimaAtualizacao": date_range}},
                        {"range": {"@timestamp": date_range}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        # Adiciona filtros à query
        if filtros:
            query["query"]["bool"]["must"].extend(filtros)
        else:
            # Se não há filtros, usa match_all
            query["query"] = {"match_all": {}}
        
        return query
    
    def buscar_processos_teste(self, tribunal, tamanho=5):
        """Executa uma busca simples para teste"""
        
        if tribunal not in self.tribunais:
            raise ValueError(f"Tribunal '{tribunal}' não encontrado. Disponíveis: {list(self.tribunais.keys())}")
        
        # Primeiro testa conexão
        sucesso, resultado = self.testar_conexao(tribunal)
        
        if not sucesso:
            print(f"❌ Falha na conexão: {resultado}")
            return None
        
        print("✅ Conexão bem-sucedida!")
        return resultado
    
    def buscar_processos(self, tribunal, classe_codigo=None, assunto_codigo=None, 
                        movimento_codigo=None, data_inicio=None, data_fim=None, tamanho=10):
        """Executa a busca na API - versão com mais tratamento de erros"""
        
        if tribunal not in self.tribunais:
            raise ValueError(f"Tribunal '{tribunal}' não encontrado. Disponíveis: {list(self.tribunais.keys())}")
        
        endpoint = self.tribunais[tribunal]
        url = f"{self.base_url}/{endpoint}/_search"
        
        # SEMPRE usa query completa para respeitar o tamanho solicitado
        query = self.construir_query(classe_codigo, assunto_codigo, movimento_codigo, 
                                   data_inicio, data_fim, tamanho)
        
        logger.info(f"URL: {url}")
        logger.info(f"Query: {json.dumps(query, indent=2)}")
        
        try:
            response = requests.post(
                url, 
                headers=self.headers, 
                json=query, 
                verify=False, 
                timeout=60  # Aumentado timeout para consultas grandes
            )
            
            # Log detalhado da resposta
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 400:
                logger.error("Erro 400 - Detalhes:")
                logger.error(f"Request URL: {response.url}")
                logger.error(f"Request Headers: {dict(response.request.headers)}")
                logger.error(f"Request Body: {response.request.body}")
                logger.error(f"Response: {response.text}")
                
                # Tenta uma query ainda mais simples com match_all
                print("🔄 Tentando query mais simples...")
                query_simples = {
                    "size": min(tamanho, 100),  # Reduz para teste
                    "query": {"match_all": {}}
                }
                
                response2 = requests.post(
                    url, 
                    headers=self.headers, 
                    json=query_simples, 
                    verify=False, 
                    timeout=30
                )
                
                if response2.status_code == 200:
                    print("✅ Query simples funcionou! Problema na estrutura da query complexa.")
                    return response2.json()
                else:
                    print(f"❌ Query simples também falhou: {response2.status_code}")
                    logger.error(f"Response simples: {response2.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
    
    def extrair_informacoes(self, resultado):
        """Extrai informações principais dos processos encontrados"""
        
        if not resultado or 'hits' not in resultado:
            return []
        
        processos = []
        for hit in resultado['hits']['hits']:
            processo = hit['_source']
            
            info = {
                'numero': processo.get('numeroProcesso', 'N/A'),
                'classe': processo.get('classe', {}).get('nome', 'N/A'),
                'orgao': processo.get('orgaoJulgador', {}).get('nome', 'N/A'),
                'data_ajuizamento': processo.get('dataAjuizamento', 'N/A'),
                'assuntos': [assunto.get('nome', 'N/A') for assunto in processo.get('assuntos', [])],
                'ultimo_movimento': None
            }
            
            # Pega o último movimento
            movimentos = processo.get('movimentos', [])
            if movimentos:
                ultimo_mov = max(movimentos, key=lambda x: x.get('dataHora', ''))
                info['ultimo_movimento'] = {
                    'nome': ultimo_mov.get('nome', 'N/A'),
                    'data': ultimo_mov.get('dataHora', 'N/A')
                }
            
            processos.append(info)
        
        return processos

def main():
    """Função principal - interface interativa com diagnósticos"""
    
    api = DataJudAPI()
    
    print("=" * 60)
    print("🏛️  BUSCA AVANÇADA NA API PÚBLICA DO DATAJUD - VERSÃO DEBUG")
    print("=" * 60)
    
    # Selecionar tribunal
    print("\n📍 Tribunais disponíveis:")
    for i, tribunal in enumerate(api.tribunais.keys(), 1):
        print(f"{i:2}. {tribunal}")
    
    while True:
        try:
            escolha = input("\nDigite o número do tribunal: ").strip()
            tribunal = list(api.tribunais.keys())[int(escolha) - 1]
            break
        except (ValueError, IndexError):
            print("❌ Escolha inválida. Tente novamente.")
    
    print(f"\n✅ Tribunal selecionado: {tribunal}")
    
    # Opção de teste simples primeiro
    teste = input("\n🔬 Fazer teste de conexão simples primeiro? (S/n): ").strip().lower()
    
    if teste != 'n':
        print(f"\n🔄 Testando conexão com {tribunal}...")
        resultado_teste = api.buscar_processos_teste(tribunal)
        
        if not resultado_teste:
            print("❌ Teste de conexão falhou. Verifique os logs acima.")
            return
        
        print(f"✅ Teste bem-sucedido! Encontrados dados no índice.")
        
        continuar = input("Continuar com busca personalizada? (S/n): ").strip().lower()
        if continuar == 'n':
            return
    
    # Coletar filtros (resto do código igual)
    print("\n🔍 Filtros de busca (pressione ENTER para pular):")
    
    classe_codigo = input("Código da classe processual: ").strip() or None
    if classe_codigo:
        try:
            classe_codigo = int(classe_codigo)
        except ValueError:
            print("❌ Código de classe inválido, ignorando.")
            classe_codigo = None
    
    assunto_codigo = input("Código do assunto: ").strip() or None
    if assunto_codigo:
        try:
            assunto_codigo = int(assunto_codigo)
        except ValueError:
            print("❌ Código de assunto inválido, ignorando.")
            assunto_codigo = None
    
    movimento_codigo = input("Código do movimento: ").strip() or None
    if movimento_codigo:
        try:
            movimento_codigo = int(movimento_codigo)
        except ValueError:
            print("❌ Código de movimento inválido, ignorando.")
            movimento_codigo = None
    
    # Intervalo de datas
    print("\n📅 Intervalo de datas (formato: YYYY-MM-DD):")
    data_inicio = input("Data início: ").strip() or None
    data_fim = input("Data fim: ").strip() or None
    
    # Validar datas
    if data_inicio:
        try:
            datetime.strptime(data_inicio, '%Y-%m-%d')
            data_inicio = f"{data_inicio}T00:00:00.000Z"
        except ValueError:
            print("❌ Data início inválida. Ignorando filtro.")
            data_inicio = None
    
    if data_fim:
        try:
            datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim = f"{data_fim}T23:59:59.999Z"
        except ValueError:
            print("❌ Data fim inválida. Ignorando filtro.")
            data_fim = None
    
    # Quantidade de resultados
    try:
        tamanho = int(input("Quantidade de processos (padrão 10): ").strip() or 10)
        tamanho = min(tamanho, 50)  # Reduzido para evitar timeouts
    except ValueError:
        tamanho = 10
    
    # Executar busca
    print(f"\n🔄 Buscando processos no {tribunal}...")
    
    resultado = api.buscar_processos(
        tribunal=tribunal,
        classe_codigo=classe_codigo,
        assunto_codigo=assunto_codigo,
        movimento_codigo=movimento_codigo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tamanho=tamanho
    )
    
    if not resultado:
        print("❌ Erro ao executar a busca. Verifique os logs acima para mais detalhes.")
        return
    
    # Processar resultados (resto igual ao original)
    total_encontrados = resultado.get('hits', {}).get('total', {})
    if isinstance(total_encontrados, dict):
        total = total_encontrados.get('value', 0)
        relacao = total_encontrados.get('relation', 'eq')
        total_texto = f"{total}{'+ ' if relacao == 'gte' else ''}"
    else:
        total_texto = str(total_encontrados)
    
    processos = api.extrair_informacoes(resultado)
    
    # Exibir resultados
    print(f"\n📊 RESULTADOS: {total_texto} processos encontrados")
    print("=" * 60)
    
    if not processos:
        print("Nenhum processo encontrado com os filtros especificados.")
        return
    
    for i, proc in enumerate(processos, 1):
        print(f"\n{i:2}. Processo: {proc['numero']}")
        print(f"    Classe: {proc['classe']}")
        print(f"    Órgão: {proc['orgao']}")
        print(f"    Ajuizamento: {proc['data_ajuizamento'][:10] if proc['data_ajuizamento'] != 'N/A' else 'N/A'}")
        
        if proc['assuntos']:
            assuntos_str = ', '.join(proc['assuntos'][:2])
            if len(proc['assuntos']) > 2:
                assuntos_str += f" (+ {len(proc['assuntos']) - 2} outros)"
            print(f"    Assuntos: {assuntos_str}")
        
        if proc['ultimo_movimento']:
            print(f"    Último movimento: {proc['ultimo_movimento']['nome']}")
            print(f"    Data movimento: {proc['ultimo_movimento']['data'][:10]}")
    
    # Salvar resultados
    salvar = input(f"\n💾 Salvar resultados em arquivo JSON? (s/N): ").strip().lower()
    if salvar in ['s', 'sim', 'y', 'yes']:
        nome_arquivo = f"datajud_{tribunal}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        dados_salvamento = {
            'tribunal': tribunal,
            'filtros': {
                'classe_codigo': classe_codigo,
                'assunto_codigo': assunto_codigo,
                'movimento_codigo': movimento_codigo,
                'data_inicio': data_inicio,
                'data_fim': data_fim
            },
            'total_encontrados': total_texto,
            'data_busca': datetime.now().isoformat(),
            'processos': processos,
            'resultado_completo': resultado
        }
        
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, ensure_ascii=False, indent=2)
            print(f"✅ Resultados salvos em: {nome_arquivo}")
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")

# Códigos de exemplo para referência
CODIGOS_EXEMPLO = {
    "classes_comuns": {
        7: "Procedimento Comum Cível",
        1: "Procedimento Ordinário",
        436: "Execução de Título Extrajudicial",
        38: "Busca e Apreensão",
        1118: "Procedimento do Juizado Especial Cível"
    },
    "assuntos_comuns": {
        7698: "Perdas e Danos",
        5547: "Responsabilidade Civil",
        11811: "Práticas Abusivas",
        1079: "Direito de Propriedade",
        9846: "Direito do Consumidor"
    },
    "movimentos_comuns": {
        26: "Distribuição",
        51: "Conclusão",
        60: "Expedição de documento",
        85: "Petição",
        92: "Publicação",
        219: "Procedência",
        246: "Definitivo"
    }
}

if __name__ == "__main__":
    print("\n📋 CÓDIGOS DE EXEMPLO PARA CONSULTA:")
    print("\n🏛️ Classes processuais comuns:")
    for codigo, nome in CODIGOS_EXEMPLO["classes_comuns"].items():
        print(f"  {codigo}: {nome}")
    
    print("\n📑 Assuntos comuns:")
    for codigo, nome in CODIGOS_EXEMPLO["assuntos_comuns"].items():
        print(f"  {codigo}: {nome}")
    
    print("\n📝 Movimentos comuns:")
    for codigo, nome in CODIGOS_EXEMPLO["movimentos_comuns"].items():
        print(f"  {codigo}: {nome}")
    
    print("\n" + "=" * 60)
    22
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Busca cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logger.exception("Erro detalhado:")
