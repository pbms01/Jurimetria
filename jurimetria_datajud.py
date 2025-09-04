#!/usr/bin/env python3
"""
Script para busca avançada na API Pública do DataJud
Permite filtrar por classe, assunto, movimento, data e tribunal
"""

import requests
import json
from datetime import datetime
import urllib3

# Desabilita warnings SSL (se necessário)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DataJudAPI:
    def __init__(self):
        self.api_key = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
        self.base_url = "https://api-publica.datajud.cnj.jus.br"
        self.headers = {
            "Authorization": f"APIKey {self.api_key}",
            "Content-Type": "application/json"
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
    
    def construir_query(self, classe_codigo=None, assunto_codigo=None, movimento_codigo=None, 
                       data_inicio=None, data_fim=None, tamanho=10):
        """Constrói a query Elasticsearch para busca"""
        
        # Query base mais simples
        query = {
            "size": tamanho,
            "query": {
                "bool": {
                    "must": []
                }
            }
        }
        
        # Filtro por classe (termo exato)
        if classe_codigo:
            query["query"]["bool"]["must"].append({
                "term": {"classe.codigo": classe_codigo}
            })
        
        # Filtro por assunto (termo exato)
        if assunto_codigo:
            query["query"]["bool"]["must"].append({
                "nested": {
                    "path": "assuntos",
                    "query": {
                        "term": {"assuntos.codigo": assunto_codigo}
                    }
                }
            })
        
        # Filtro por movimento (termo exato)
        if movimento_codigo:
            query["query"]["bool"]["must"].append({
                "nested": {
                    "path": "movimentos",
                    "query": {
                        "term": {"movimentos.codigo": movimento_codigo}
                    }
                }
            })
        
        # Filtro por intervalo de datas
        if data_inicio or data_fim:
            date_range = {}
            if data_inicio:
                date_range["gte"] = data_inicio
            if data_fim:
                date_range["lte"] = data_fim
            
            query["query"]["bool"]["must"].append({
                "range": {
                    "dataAjuizamento": date_range
                }
            })
        
        # Se não há filtros específicos, busca todos
        if not query["query"]["bool"]["must"]:
            query["query"] = {"match_all": {}}
        
        return query
    
    def buscar_processos(self, tribunal, classe_codigo=None, assunto_codigo=None, 
                        movimento_codigo=None, data_inicio=None, data_fim=None, tamanho=10):
        """Executa a busca na API"""
        
        if tribunal not in self.tribunais:
            raise ValueError(f"Tribunal '{tribunal}' não encontrado. Disponíveis: {list(self.tribunais.keys())}")
        
        endpoint = self.tribunais[tribunal]
        url = f"{self.base_url}/{endpoint}/_search"
        
        query = self.construir_query(classe_codigo, assunto_codigo, movimento_codigo, 
                                   data_inicio, data_fim, tamanho)
        
        try:
            response = requests.post(url, headers=self.headers, json=query, 
                                   verify=False, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
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
    """Função principal - interface interativa"""
    
    api = DataJudAPI()
    
    print("=" * 60)
    print("🏛️  BUSCA AVANÇADA NA API PÚBLICA DO DATAJUD")
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
    
    # Coletar filtros
    print("\n🔍 Filtros de busca (pressione ENTER para pular):")
    
    classe_codigo = input("Código da classe processual: ").strip() or None
    if classe_codigo:
        classe_codigo = int(classe_codigo)
    
    assunto_codigo = input("Código do assunto: ").strip() or None
    if assunto_codigo:
        assunto_codigo = int(assunto_codigo)
    
    movimento_codigo = input("Código do movimento: ").strip() or None
    if movimento_codigo:
        movimento_codigo = int(movimento_codigo)
    
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
        tamanho = min(tamanho, 100)  # Limita a 100
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
        print("❌ Erro ao executar a busca.")
        return
    
    # Processar resultados
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
            assuntos_str = ', '.join(proc['assuntos'][:2])  # Primeiros 2 assuntos
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
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Busca cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")