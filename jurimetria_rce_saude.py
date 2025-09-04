#!/usr/bin/env python3
"""
ANÁLISE COMPLETA DE JURIMETRIA: RCE EM SAÚDE PÚBLICA - VERSÃO FINAL
Script completo para coleta, análise e exportação para Excel

Execução: python3 jurimetria_rce_saude_final.py

Autor: Análise Datajud
Data: 2025-08-25
Versão: 2.0 (com correções de data)
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import sys
import os
import warnings
warnings.filterwarnings('ignore')

class JurimetriaRCESaudeFinal:
    """
    Classe final para análise de jurimetria RCE em Saúde Pública
    Versão corrigida com tratamento robusto de datas e erros
    """
    
    def __init__(self, api_key: str, tribunal: str = 'TJMT'):
        """Inicializa a análise"""
        self.api_key = api_key
        self.tribunal = tribunal.upper()
        self.url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal.lower()}/_search"
        
        self.headers = {
            "Authorization": f"APIKey {api_key}",
            "Content-Type": "application/json"
        }
        
        # Códigos identificados na estratégia
        self.codigos_rce_saude = [10069, 12491, 11883, 12489, 10283, 12223, 12511, 10282, 8934, 10064]
        self.codigos_tutela = [51, 60, 85, 26, 581, 454]
        
        # Armazenamento de dados
        self.dados_coletados = {}
        self.metricas_calculadas = {}
        
        print(f"🚀 ANÁLISE DE JURIMETRIA RCE+SAÚDE - VERSÃO FINAL")
        print(f"📊 Tribunal: {self.tribunal}")
        print(f"🎯 Códigos RCE+Saúde: {len(self.codigos_rce_saude)}")
        print(f"⚖️ Códigos Tutela: {len(self.codigos_tutela)}")
        print(f"{'='*70}")
    
    def _fazer_requisicao(self, query: Dict, descricao: str = "", timeout: int = 30) -> Optional[Dict]:
        """Executa requisição com tratamento de erro e retry"""
        max_tentativas = 3
        
        for tentativa in range(max_tentativas):
            try:
                if descricao:
                    print(f"🔍 {descricao} (tentativa {tentativa + 1})")
                
                response = requests.post(self.url, headers=self.headers, json=query, timeout=timeout)
                
                if response.status_code == 200:
                    resultado = response.json()
                    print(f"   ✅ Sucesso | Tempo: {response.elapsed.total_seconds():.2f}s")
                    return resultado
                else:
                    print(f"   ❌ Erro {response.status_code}")
                    if tentativa < max_tentativas - 1:
                        time.sleep(2)
                        continue
                    return None
                    
            except Exception as e:
                print(f"   ❌ Erro: {str(e)[:50]}...")
                if tentativa < max_tentativas - 1:
                    time.sleep(2)
                    continue
                return None
        
        return None
    
    def _tratar_data(self, data_str: str) -> Optional[str]:
        """Trata datas problemáticas"""
        if not data_str:
            return None
        
        try:
            # Remove datas futuras irreais (após 2030)
            if '2263' in data_str or '2262' in data_str or '2261' in data_str:
                return None
            
            # Converte para datetime e valida
            dt = pd.to_datetime(data_str, errors='coerce')
            if pd.isna(dt):
                return None
            
            # Verifica se a data é razoável (entre 1990 e 2030)
            if dt.year < 1990 or dt.year > 2030:
                return None
            
            return data_str
        except:
            return None
    
    def coletar_processos_detalhados(self, size: int = 2000) -> pd.DataFrame:
        """Coleta processos detalhados para análise"""
        print(f"\n📋 COLETANDO PROCESSOS DETALHADOS")
        
        query = {
            "size": size,
            "query": {
                "terms": {"assuntos.codigo": self.codigos_rce_saude}
            },
            "_source": [
                "numeroProcesso", "classe.codigo", "classe.nome", 
                "assuntos.codigo", "assuntos.nome",
                "dataAjuizamento", "dataHoraUltimaAtualizacao",
                "orgaoJulgador.codigo", "orgaoJulgador.nome",
                "movimentos.codigo", "movimentos.nome", "movimentos.dataHora"
            ],
            "sort": [{"dataAjuizamento": {"order": "desc"}}]
        }
        
        resultado = self._fazer_requisicao(query, f"Coletando {size} processos detalhados")
        
        if not resultado or 'hits' not in resultado:
            print("❌ Erro ao coletar processos")
            return pd.DataFrame()
        
        processos = []
        
        for hit in resultado['hits']['hits']:
            source = hit['_source']
            
            # Trata datas
            data_ajuizamento = self._tratar_data(source.get('dataAjuizamento', ''))
            data_ultima_atualizacao = self._tratar_data(source.get('dataHoraUltimaAtualizacao', ''))
            
            # Dados básicos do processo
            processo_base = {
                'numero_processo': source.get('numeroProcesso', ''),
                'classe_codigo': source.get('classe', {}).get('codigo', ''),
                'classe_nome': source.get('classe', {}).get('nome', ''),
                'data_ajuizamento': data_ajuizamento,
                'data_ultima_atualizacao': data_ultima_atualizacao,
                'orgao_codigo': source.get('orgaoJulgador', {}).get('codigo', ''),
                'orgao_nome': source.get('orgaoJulgador', {}).get('nome', ''),
            }
            
            # Assuntos do processo
            assuntos = source.get('assuntos', [])
            assuntos_codigos = []
            assuntos_nomes = []
            
            for assunto in assuntos:
                if isinstance(assunto, dict):
                    codigo = assunto.get('codigo', '')
                    nome = assunto.get('nome', '')
                    if codigo:
                        assuntos_codigos.append(str(codigo))
                    if nome:
                        assuntos_nomes.append(nome)
            
            processo_base['assuntos_codigos'] = '; '.join(assuntos_codigos)
            processo_base['assuntos_nomes'] = '; '.join(assuntos_nomes)
            
            # Análise de movimentos
            movimentos = source.get('movimentos', [])
            
            # Flags de análise
            tem_tutela = False
            tem_acordo = False
            tem_deferimento = False
            tem_indeferimento = False
            tem_sentenca = False
            
            movimentos_tutela = []
            movimentos_acordo = []
            data_primeira_tutela = None
            data_primeiro_acordo = None
            
            for movimento in movimentos:
                if isinstance(movimento, dict):
                    mov_codigo = movimento.get('codigo', 0)
                    mov_nome = movimento.get('nome', '').lower()
                    mov_data = self._tratar_data(movimento.get('dataHora', ''))
                    
                    # Verifica tutela
                    if mov_codigo in self.codigos_tutela:
                        tem_tutela = True
                        movimentos_tutela.append(f"{mov_codigo}")
                        if mov_data and (not data_primeira_tutela or mov_data < data_primeira_tutela):
                            data_primeira_tutela = mov_data
                    
                    # Verifica acordo
                    if any(termo in mov_nome for termo in ['acordo', 'homologação', 'conciliação', 'mediação']):
                        tem_acordo = True
                        movimentos_acordo.append(f"{mov_codigo}")
                        if mov_data and (not data_primeiro_acordo or mov_data < data_primeiro_acordo):
                            data_primeiro_acordo = mov_data
                    
                    # Verifica deferimento/indeferimento
                    if 'deferimento' in mov_nome and 'indeferimento' not in mov_nome:
                        tem_deferimento = True
                    elif 'indeferimento' in mov_nome:
                        tem_indeferimento = True
                    
                    # Verifica sentença
                    if any(termo in mov_nome for termo in ['sentença', 'julgamento', 'decisão']):
                        tem_sentenca = True
            
            # Adiciona flags ao processo
            processo_base.update({
                'tem_tutela': tem_tutela,
                'tem_acordo': tem_acordo,
                'tem_deferimento': tem_deferimento,
                'tem_indeferimento': tem_indeferimento,
                'tem_sentenca': tem_sentenca,
                'tutela_e_acordo': tem_tutela and tem_acordo,
                'movimentos_tutela': '; '.join(set(movimentos_tutela)),
                'movimentos_acordo': '; '.join(set(movimentos_acordo)),
                'data_primeira_tutela': data_primeira_tutela,
                'data_primeiro_acordo': data_primeiro_acordo,
                'total_movimentos': len(movimentos)
            })
            
            # Cálculo de tempo até acordo (se houver)
            if data_primeira_tutela and data_primeiro_acordo:
                try:
                    dt_tutela = pd.to_datetime(data_primeira_tutela)
                    dt_acordo = pd.to_datetime(data_primeiro_acordo)
                    if pd.notna(dt_tutela) and pd.notna(dt_acordo):
                        processo_base['dias_tutela_acordo'] = (dt_acordo - dt_tutela).days
                    else:
                        processo_base['dias_tutela_acordo'] = None
                except:
                    processo_base['dias_tutela_acordo'] = None
            else:
                processo_base['dias_tutela_acordo'] = None
            
            # Cálculo de tempo de tramitação
            if data_ajuizamento and data_ultima_atualizacao:
                try:
                    dt_inicio = pd.to_datetime(data_ajuizamento)
                    dt_fim = pd.to_datetime(data_ultima_atualizacao)
                    if pd.notna(dt_inicio) and pd.notna(dt_fim):
                        processo_base['dias_tramitacao'] = (dt_fim - dt_inicio).days
                    else:
                        processo_base['dias_tramitacao'] = None
                except:
                    processo_base['dias_tramitacao'] = None
            else:
                processo_base['dias_tramitacao'] = None
            
            processos.append(processo_base)
        
        df = pd.DataFrame(processos)
        
        print(f"✅ Coletados {len(df)} processos detalhados")
        print(f"   📊 Com tutela: {df['tem_tutela'].sum()}")
        print(f"   🤝 Com acordo: {df['tem_acordo'].sum()}")
        print(f"   🎯 Tutela + Acordo: {df['tutela_e_acordo'].sum()}")
        
        self.dados_coletados['processos_detalhados'] = df
        return df
    
    def calcular_metricas_completas(self, df_processos: pd.DataFrame) -> Dict:
        """Calcula todas as métricas de jurimetria"""
        print(f"\n📈 CALCULANDO MÉTRICAS COMPLETAS")
        
        if df_processos.empty:
            return {}
        
        total_processos = len(df_processos)
        
        # Métricas básicas
        metricas = {
            'total_processos': total_processos,
            'processos_com_tutela': int(df_processos['tem_tutela'].sum()),
            'processos_com_acordo': int(df_processos['tem_acordo'].sum()),
            'processos_tutela_e_acordo': int(df_processos['tutela_e_acordo'].sum()),
            'processos_com_deferimento': int(df_processos['tem_deferimento'].sum()),
            'processos_com_indeferimento': int(df_processos['tem_indeferimento'].sum()),
            'processos_com_sentenca': int(df_processos['tem_sentenca'].sum())
        }
        
        # Taxas percentuais
        metricas['taxa_tutela'] = round((metricas['processos_com_tutela'] / total_processos * 100), 2) if total_processos > 0 else 0
        metricas['taxa_acordo'] = round((metricas['processos_com_acordo'] / total_processos * 100), 2) if total_processos > 0 else 0
        metricas['taxa_tutela_e_acordo'] = round((metricas['processos_tutela_e_acordo'] / total_processos * 100), 2) if total_processos > 0 else 0
        
        # Efetividade das tutelas
        if metricas['processos_com_tutela'] > 0:
            metricas['efetividade_tutela'] = round((metricas['processos_tutela_e_acordo'] / metricas['processos_com_tutela'] * 100), 2)
        else:
            metricas['efetividade_tutela'] = 0
        
        # Taxa de deferimento
        total_decisoes = metricas['processos_com_deferimento'] + metricas['processos_com_indeferimento']
        if total_decisoes > 0:
            metricas['taxa_deferimento'] = round((metricas['processos_com_deferimento'] / total_decisoes * 100), 2)
            metricas['taxa_indeferimento'] = round((metricas['processos_com_indeferimento'] / total_decisoes * 100), 2)
        else:
            metricas['taxa_deferimento'] = 0
            metricas['taxa_indeferimento'] = 0
        
        # Métricas temporais (com tratamento de valores nulos)
        df_com_tempo = df_processos.dropna(subset=['dias_tramitacao'])
        if not df_com_tempo.empty:
            metricas['tempo_medio_tramitacao'] = round(df_com_tempo['dias_tramitacao'].mean(), 0)
            metricas['tempo_mediano_tramitacao'] = round(df_com_tempo['dias_tramitacao'].median(), 0)
            metricas['tempo_min_tramitacao'] = int(df_com_tempo['dias_tramitacao'].min())
            metricas['tempo_max_tramitacao'] = int(df_com_tempo['dias_tramitacao'].max())
        else:
            metricas['tempo_medio_tramitacao'] = 0
            metricas['tempo_mediano_tramitacao'] = 0
            metricas['tempo_min_tramitacao'] = 0
            metricas['tempo_max_tramitacao'] = 0
        
        df_tutela_acordo = df_processos.dropna(subset=['dias_tutela_acordo'])
        if not df_tutela_acordo.empty:
            metricas['tempo_medio_tutela_acordo'] = round(df_tutela_acordo['dias_tutela_acordo'].mean(), 0)
            metricas['tempo_mediano_tutela_acordo'] = round(df_tutela_acordo['dias_tutela_acordo'].median(), 0)
        else:
            metricas['tempo_medio_tutela_acordo'] = 0
            metricas['tempo_mediano_tutela_acordo'] = 0
        
        print(f"✅ Métricas calculadas:")
        print(f"   📊 Total de processos: {metricas['total_processos']:,}")
        print(f"   🎯 Taxa de tutelas: {metricas['taxa_tutela']:.1f}%")
        print(f"   🤝 Taxa de acordos: {metricas['taxa_acordo']:.1f}%")
        print(f"   ⚖️ Efetividade das tutelas: {metricas['efetividade_tutela']:.1f}%")
        
        self.metricas_calculadas = metricas
        return metricas
    
    def criar_dataframes_para_excel(self) -> Dict[str, pd.DataFrame]:
        """Cria DataFrames estruturados para exportação Excel"""
        print(f"\n📋 PREPARANDO DADOS PARA EXCEL")
        
        dfs = {}
        
        # 1. Resumo Executivo
        if self.metricas_calculadas:
            resumo_data = {
                'Métrica': [
                    'Total de Processos',
                    'Processos com Tutela',
                    'Processos com Acordo',
                    'Tutela + Acordo',
                    'Efetividade das Tutelas (%)',
                    'Taxa de Deferimento (%)',
                    'Tempo Médio Tramitação (dias)',
                    'Tempo Médio Tutela→Acordo (dias)'
                ],
                'Valor': [
                    f"{self.metricas_calculadas['total_processos']:,}",
                    f"{self.metricas_calculadas['processos_com_tutela']:,}",
                    f"{self.metricas_calculadas['processos_com_acordo']:,}",
                    f"{self.metricas_calculadas['processos_tutela_e_acordo']:,}",
                    f"{self.metricas_calculadas['efetividade_tutela']:.1f}%",
                    f"{self.metricas_calculadas['taxa_deferimento']:.1f}%",
                    f"{self.metricas_calculadas['tempo_medio_tramitacao']:.0f}",
                    f"{self.metricas_calculadas['tempo_medio_tutela_acordo']:.0f}"
                ],
                'Percentual': [
                    '100.0%',
                    f"{self.metricas_calculadas['taxa_tutela']:.1f}%",
                    f"{self.metricas_calculadas['taxa_acordo']:.1f}%",
                    f"{self.metricas_calculadas['taxa_tutela_e_acordo']:.1f}%",
                    '-',
                    '-',
                    '-',
                    '-'
                ]
            }
            
            dfs['Resumo_Executivo'] = pd.DataFrame(resumo_data)
        
        # 2. Processos Detalhados (limitado para não sobrecarregar)
        if 'processos_detalhados' in self.dados_coletados:
            df_processos = self.dados_coletados['processos_detalhados'].copy()
            
            # Seleciona colunas principais
            colunas_principais = [
                'numero_processo', 'classe_codigo', 'classe_nome',
                'data_ajuizamento', 'orgao_nome',
                'tem_tutela', 'tem_acordo', 'tutela_e_acordo',
                'dias_tramitacao', 'dias_tutela_acordo',
                'total_movimentos'
            ]
            
            df_processos_excel = df_processos[colunas_principais].copy()
            
            # Renomeia colunas para Excel
            df_processos_excel.columns = [
                'Número do Processo', 'Código da Classe', 'Nome da Classe',
                'Data Ajuizamento', 'Órgão Julgador',
                'Tem Tutela', 'Tem Acordo', 'Tutela e Acordo',
                'Dias Tramitação', 'Dias Tutela→Acordo',
                'Total Movimentos'
            ]
            
            dfs['Processos_Detalhados'] = df_processos_excel
        
        # 3. Análise por Classe
        if 'processos_detalhados' in self.dados_coletados:
            df_processos = self.dados_coletados['processos_detalhados']
            
            analise_classe = df_processos.groupby(['classe_codigo', 'classe_nome']).agg({
                'numero_processo': 'count',
                'tem_tutela': 'sum',
                'tem_acordo': 'sum',
                'tutela_e_acordo': 'sum'
            }).reset_index()
            
            analise_classe.columns = [
                'Código', 'Nome', 'Total_Processos', 
                'Com_Tutela', 'Com_Acordo', 'Tutela_e_Acordo'
            ]
            
            # Calcula taxas
            analise_classe['Taxa_Tutela'] = (analise_classe['Com_Tutela'] / analise_classe['Total_Processos'] * 100).round(1)
            analise_classe['Taxa_Acordo'] = (analise_classe['Com_Acordo'] / analise_classe['Total_Processos'] * 100).round(1)
            analise_classe['Efetividade_Tutela'] = (analise_classe['Tutela_e_Acordo'] / analise_classe['Com_Tutela'] * 100).round(1)
            
            # Ordena por total de processos
            analise_classe = analise_classe.sort_values('Total_Processos', ascending=False)
            
            dfs['Analise_por_Classe'] = analise_classe
        
        # 4. Análise Temporal
        if 'processos_detalhados' in self.dados_coletados:
            df_processos = self.dados_coletados['processos_detalhados'].copy()
            
            # Extrai ano da data de ajuizamento
            df_processos['ano_ajuizamento'] = pd.to_datetime(df_processos['data_ajuizamento'], errors='coerce').dt.year
            
            # Remove anos inválidos
            df_processos = df_processos.dropna(subset=['ano_ajuizamento'])
            df_processos = df_processos[(df_processos['ano_ajuizamento'] >= 2000) & (df_processos['ano_ajuizamento'] <= 2025)]
            
            if not df_processos.empty:
                analise_temporal = df_processos.groupby('ano_ajuizamento').agg({
                    'numero_processo': 'count',
                    'tem_tutela': 'sum',
                    'tem_acordo': 'sum',
                    'tutela_e_acordo': 'sum'
                }).reset_index()
                
                analise_temporal.columns = [
                    'Ano', 'Total_Processos', 'Com_Tutela', 'Com_Acordo', 'Tutela_e_Acordo'
                ]
                
                # Calcula taxas
                analise_temporal['Taxa_Tutela'] = (analise_temporal['Com_Tutela'] / analise_temporal['Total_Processos'] * 100).round(1)
                analise_temporal['Taxa_Acordo'] = (analise_temporal['Com_Acordo'] / analise_temporal['Total_Processos'] * 100).round(1)
                
                dfs['Analise_Temporal'] = analise_temporal
        
        # 5. Teste de Hipótese
        if self.metricas_calculadas:
            criterios = []
            
            # Critério 1: Taxa de tutelas significativa
            taxa_tutela = self.metricas_calculadas['taxa_tutela']
            criterios.append({
                'Critério': 'Taxa de Tutelas > 5%',
                'Valor': f"{taxa_tutela:.1f}%",
                'Status': '✅ Atendido' if taxa_tutela > 5 else '❌ Não Atendido'
            })
            
            # Critério 2: Efetividade positiva
            efetividade = self.metricas_calculadas['efetividade_tutela']
            criterios.append({
                'Critério': 'Efetividade > 0%',
                'Valor': f"{efetividade:.1f}%",
                'Status': '✅ Atendido' if efetividade > 0 else '❌ Não Atendido'
            })
            
            # Critério 3: Taxa de deferimento
            taxa_deferimento = self.metricas_calculadas['taxa_deferimento']
            criterios.append({
                'Critério': 'Taxa Deferimento > 50%',
                'Valor': f"{taxa_deferimento:.1f}%",
                'Status': '✅ Atendido' if taxa_deferimento > 50 else '❌ Não Atendido'
            })
            
            dfs['Teste_Hipotese'] = pd.DataFrame(criterios)
        
        print(f"✅ Preparados {len(dfs)} DataFrames para Excel")
        return dfs
    
    def exportar_para_excel(self, nome_arquivo: str = None) -> str:
        """Exporta todos os dados para Excel formatado"""
        if not nome_arquivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"jurimetria_rce_saude_{self.tribunal.lower()}_{timestamp}.xlsx"
        
        print(f"\n📊 EXPORTANDO PARA EXCEL: {nome_arquivo}")
        
        # Prepara DataFrames
        dfs = self.criar_dataframes_para_excel()
        
        if not dfs:
            print("❌ Nenhum dado para exportar")
            return ""
        
        # Cria arquivo Excel
        try:
            with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
                
                # Escreve cada DataFrame em uma aba
                for nome_aba, df in dfs.items():
                    df.to_excel(writer, sheet_name=nome_aba, index=False)
                    
                    # Formatação básica
                    worksheet = writer.sheets[nome_aba]
                    
                    # Ajusta largura das colunas
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ Excel exportado com sucesso!")
            print(f"   📁 Arquivo: {nome_arquivo}")
            print(f"   📋 Abas: {list(dfs.keys())}")
            
            return nome_arquivo
            
        except Exception as e:
            print(f"❌ Erro ao exportar Excel: {e}")
            return ""
    
    def executar_analise_completa(self, size_processos: int = 2000) -> str:
        """Executa análise completa e exporta para Excel"""
        print(f"\n🚀 EXECUTANDO ANÁLISE COMPLETA")
        print(f"{'='*70}")
        
        try:
            # 1. Coleta processos detalhados
            df_processos = self.coletar_processos_detalhados(size_processos)
            
            if df_processos.empty:
                print("❌ Erro: Nenhum processo coletado")
                return ""
            
            # 2. Calcula métricas
            self.calcular_metricas_completas(df_processos)
            
            # 3. Exporta para Excel
            arquivo_excel = self.exportar_para_excel()
            
            # 4. Relatório final
            print(f"\n{'='*70}")
            print(f"🎯 ANÁLISE COMPLETA FINALIZADA")
            print(f"{'='*70}")
            print(f"📊 Processos analisados: {len(df_processos):,}")
            print(f"📈 Métricas calculadas: {len(self.metricas_calculadas)}")
            print(f"📋 Arquivo Excel: {arquivo_excel}")
            print(f"✅ Análise pronta para uso!")
            
            return arquivo_excel
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            import traceback
            traceback.print_exc()
            return ""

def main():
    """Função principal para execução via terminal"""
    print(f"""
{'='*70}
🏛️  ANÁLISE DE JURIMETRIA: RCE EM SAÚDE PÚBLICA
📊 Responsabilidade Civil do Estado - Tribunal de Justiça
⚖️  Análise de Tutelas de Urgência e Efetividade
🔧 VERSÃO FINAL - Com correções de data e erro
{'='*70}
""")
    
    # Configurações
    API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
    TRIBUNAL = "TJMT"
    SIZE_PROCESSOS = 2000  # Número de processos a coletar
    
    print(f"⚙️  CONFIGURAÇÕES:")
    print(f"   🏛️  Tribunal: {TRIBUNAL}")
    print(f"   📊 Processos a coletar: {SIZE_PROCESSOS:,}")
    print(f"   🔑 API Key: {'*' * 20}...{API_KEY[-10:]}")
    
    # Confirmação
    try:
        resposta = input(f"\n🤔 Deseja prosseguir com a análise? (s/N): ").strip().lower()
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Análise cancelada pelo usuário")
            return
    except:
        # Se não conseguir ler input (execução automatizada), prossegue
        print("🤖 Execução automatizada - prosseguindo...")
    
    # Executa análise
    try:
        jurimetria = JurimetriaRCESaudeFinal(API_KEY, TRIBUNAL)
        arquivo_excel = jurimetria.executar_analise_completa(SIZE_PROCESSOS)
        
        if arquivo_excel:
            print(f"\n🎉 SUCESSO!")
            print(f"📁 Arquivo gerado: {arquivo_excel}")
            print(f"📊 Abra o arquivo Excel para visualizar todos os dados")
            print(f"⚖️  Análise de jurimetria completa!")
        else:
            print(f"\n❌ ERRO: Falha na geração do arquivo Excel")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Análise interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

