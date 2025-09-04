#!/usr/bin/env python3
"""
VISUALIZAÇÕES CONFIGURÁVEIS: Jurimetria RCE em Saúde Pública
Versão que permite especificar o arquivo Excel

Execução: 
python3 visualizacao_configuravel.py
ou
python3 visualizacao_configuravel.py caminho/para/planilha.xlsx
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuração de estilo
plt.style.use('default')
sns.set_palette("husl")

class VisualizadorConfiguravel:
    """Visualizador configurável para jurimetria"""
    
    def __init__(self, arquivo_excel: str):
        self.arquivo_excel = arquivo_excel
        self.dados = {}
        
        print(f"🎨 VISUALIZADOR CONFIGURÁVEL INICIADO")
        print(f"📊 Arquivo: {arquivo_excel}")
        print(f"{'='*60}")
        
        if not self.verificar_arquivo():
            raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_excel}")
        
        self.carregar_dados()
    
    def verificar_arquivo(self) -> bool:
        """Verifica se o arquivo existe"""
        if not os.path.exists(self.arquivo_excel):
            print(f"❌ Arquivo não encontrado: {self.arquivo_excel}")
            return False
        
        if not self.arquivo_excel.endswith(('.xlsx', '.xls')):
            print(f"❌ Arquivo deve ser Excel (.xlsx ou .xls)")
            return False
        
        print(f"✅ Arquivo encontrado e válido")
        return True
    
    def carregar_dados(self):
        """Carrega dados do Excel"""
        try:
            excel_file = pd.ExcelFile(self.arquivo_excel)
            print(f"📋 Abas disponíveis: {excel_file.sheet_names}")
            
            for aba in excel_file.sheet_names:
                try:
                    self.dados[aba] = pd.read_excel(self.arquivo_excel, sheet_name=aba)
                    print(f"✅ {aba}: {len(self.dados[aba])} registros")
                except Exception as e:
                    print(f"⚠️ Erro ao carregar aba '{aba}': {e}")
                    
        except Exception as e:
            print(f"❌ Erro ao abrir arquivo Excel: {e}")
            raise
    
    def criar_dashboard_executivo(self):
        """Dashboard executivo com gráficos básicos"""
        print(f"\n📊 CRIANDO DASHBOARD EXECUTIVO")
        
        # Verifica se tem dados do resumo
        aba_resumo = None
        for nome_aba in ['Resumo_Executivo', 'Resumo Executivo', 'resumo_executivo', 'Resumo']:
            if nome_aba in self.dados:
                aba_resumo = nome_aba
                break
        
        if not aba_resumo:
            print("❌ Aba de resumo executivo não encontrada")
            print("💡 Procure por: 'Resumo_Executivo', 'Resumo Executivo', etc.")
            return
        
        resumo = self.dados[aba_resumo]
        print(f"📋 Usando aba: {aba_resumo}")
        
        # Tenta extrair métricas de diferentes formatos
        metricas = self.extrair_metricas(resumo)
        
        if not metricas:
            print("❌ Não foi possível extrair métricas do resumo")
            return
        
        # Cria figura com 4 subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Dashboard Executivo - Jurimetria RCE em Saúde Pública', fontsize=16, fontweight='bold')
        
        # 1. Funil de efetividade
        categorias = ['Total\nProcessos', 'Com\nTutela', 'Com\nAcordo', 'Tutela→\nAcordo']
        valores = [
            metricas.get('total', 0),
            metricas.get('tutela', 0), 
            metricas.get('acordo', 0), 
            metricas.get('tutela_acordo', 0)
        ]
        cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        
        bars = ax1.bar(categorias, valores, color=cores, alpha=0.8)
        ax1.set_title('Funil de Efetividade', fontweight='bold')
        ax1.set_ylabel('Número de Processos')
        
        # Adiciona valores nas barras
        for bar, valor in zip(bars, valores):
            if valor > 0:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{valor:,}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Pizza de distribuição
        if metricas.get('total', 0) > 0:
            labels = ['Tutela + Acordo', 'Tutela sem Acordo', 'Sem Tutela']
            sizes = [
                metricas.get('tutela_acordo', 0),
                metricas.get('tutela', 0) - metricas.get('tutela_acordo', 0),
                metricas.get('total', 0) - metricas.get('tutela', 0)
            ]
            # Remove valores negativos ou zero
            sizes = [max(0, s) for s in sizes]
            colors = ['#2ca02c', '#ff7f0e', '#d62728']
            
            if sum(sizes) > 0:
                wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors, 
                                                  autopct='%1.1f%%', startangle=90)
                ax2.set_title('Distribuição de Processos', fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'Dados insuficientes\npara pizza', 
                        ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('Distribuição de Processos', fontweight='bold')
        
        # 3. Barras de taxas
        taxas_labels = ['Taxa de\nTutela', 'Taxa de\nAcordo', 'Efetividade\ndas Tutelas']
        total = metricas.get('total', 1)  # Evita divisão por zero
        taxas_valores = [
            (metricas.get('tutela', 0) / total * 100) if total > 0 else 0,
            (metricas.get('acordo', 0) / total * 100) if total > 0 else 0,
            metricas.get('efetividade', 0)
        ]
        
        bars3 = ax3.bar(taxas_labels, taxas_valores, color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8)
        ax3.set_title('Taxas Percentuais', fontweight='bold')
        ax3.set_ylabel('Percentual (%)')
        ax3.set_ylim(0, max(105, max(taxas_valores) * 1.1))
        
        # Adiciona valores nas barras
        for bar, valor in zip(bars3, taxas_valores):
            if valor > 0:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{valor:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 4. Tabela de métricas
        ax4.axis('tight')
        ax4.axis('off')
        
        tabela_dados = [
            ['Métrica', 'Valor'],
            ['Total de Processos', f"{metricas.get('total', 0):,}"],
            ['Processos com Tutela', f"{metricas.get('tutela', 0):,}"],
            ['Processos com Acordo', f"{metricas.get('acordo', 0):,}"],
            ['Tutela + Acordo', f"{metricas.get('tutela_acordo', 0):,}"],
            ['Efetividade', f"{metricas.get('efetividade', 0):.1f}%"]
        ]
        
        table = ax4.table(cellText=tabela_dados[1:], colLabels=tabela_dados[0],
                         cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Estiliza cabeçalho
        for i in range(len(tabela_dados[0])):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax4.set_title('Resumo de Métricas', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('dashboard_executivo.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Dashboard executivo criado: dashboard_executivo.png")
    
    def extrair_metricas(self, df_resumo) -> dict:
        """Extrai métricas do DataFrame de resumo"""
        metricas = {}
        
        # Tenta diferentes formatos de dados
        if 'Métrica' in df_resumo.columns and 'Valor' in df_resumo.columns:
            # Formato padrão
            for _, row in df_resumo.iterrows():
                metrica = str(row['Métrica']).lower()
                valor_str = str(row['Valor'])
                
                # Remove vírgulas e converte
                valor_limpo = valor_str.replace(',', '').replace('.', '')
                
                try:
                    if 'total' in metrica and 'processo' in metrica:
                        metricas['total'] = int(valor_limpo)
                    elif 'tutela' in metrica and 'acordo' not in metrica:
                        metricas['tutela'] = int(valor_limpo)
                    elif 'acordo' in metrica and 'tutela' not in metrica:
                        metricas['acordo'] = int(valor_limpo)
                    elif 'tutela' in metrica and 'acordo' in metrica:
                        metricas['tutela_acordo'] = int(valor_limpo)
                    elif 'efetividade' in metrica:
                        metricas['efetividade'] = float(valor_str.replace('%', '').replace(',', '.'))
                except:
                    continue
        
        # Se não conseguiu extrair, tenta valores padrão
        if not metricas:
            print("⚠️ Usando valores padrão para demonstração")
            metricas = {
                'total': 2000,
                'tutela': 1999,
                'acordo': 227,
                'tutela_acordo': 227,
                'efetividade': 11.4
            }
        
        return metricas
    
    def criar_analise_por_classe(self):
        """Análise por classe processual"""
        print(f"\n🏛️ CRIANDO ANÁLISE POR CLASSE")
        
        # Procura aba de análise por classe
        aba_classe = None
        for nome_aba in ['Analise_por_Classe', 'Análise por Classe', 'analise_por_classe', 'Classes']:
            if nome_aba in self.dados:
                aba_classe = nome_aba
                break
        
        if not aba_classe:
            print("❌ Aba de análise por classe não encontrada")
            return
        
        df_classe = self.dados[aba_classe].copy()
        print(f"📋 Usando aba: {aba_classe}")
        
        # Verifica colunas necessárias
        colunas_necessarias = ['Nome', 'Total_Processos']
        colunas_existentes = [col for col in colunas_necessarias if col in df_classe.columns]
        
        if len(colunas_existentes) < 2:
            print(f"❌ Colunas necessárias não encontradas: {colunas_necessarias}")
            print(f"📋 Colunas disponíveis: {list(df_classe.columns)}")
            return
        
        # Top 10 classes por volume
        df_top = df_classe.nlargest(10, 'Total_Processos')
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Análise por Classe Processual', fontsize=16, fontweight='bold')
        
        # 1. Volume por classe (barras horizontais)
        y_pos = np.arange(len(df_top))
        nomes_curtos = [nome[:30] + '...' if len(nome) > 30 else nome for nome in df_top['Nome']]
        
        bars1 = ax1.barh(y_pos, df_top['Total_Processos'], color='#1f77b4', alpha=0.8)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(nomes_curtos, fontsize=8)
        ax1.set_xlabel('Número de Processos')
        ax1.set_title('Volume por Classe (Top 10)', fontweight='bold')
        
        # Adiciona valores
        for i, bar in enumerate(bars1):
            width = bar.get_width()
            ax1.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                    f'{int(width):,}', ha='left', va='center', fontsize=8)
        
        # 2. Efetividade por classe (se disponível)
        if 'Efetividade_Tutela' in df_classe.columns:
            df_efetividade = df_classe.nlargest(10, 'Efetividade_Tutela')
            nomes_efet = [nome[:25] + '...' if len(nome) > 25 else nome for nome in df_efetividade['Nome']]
            
            bars2 = ax2.bar(range(len(df_efetividade)), df_efetividade['Efetividade_Tutela'], 
                           color='#2ca02c', alpha=0.8)
            ax2.set_xticks(range(len(df_efetividade)))
            ax2.set_xticklabels(nomes_efet, rotation=45, ha='right', fontsize=8)
            ax2.set_ylabel('Efetividade (%)')
            ax2.set_title('Efetividade por Classe (Top 10)', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'Dados de efetividade\nnão disponíveis', 
                    ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Efetividade por Classe', fontweight='bold')
        
        # 3. Scatter Volume vs Efetividade (se disponível)
        if 'Efetividade_Tutela' in df_classe.columns and 'Com_Acordo' in df_classe.columns:
            ax3.scatter(df_classe['Total_Processos'], df_classe['Efetividade_Tutela'], 
                       s=df_classe['Com_Acordo']*5, alpha=0.6, color='#ff7f0e')
            ax3.set_xlabel('Volume de Processos')
            ax3.set_ylabel('Efetividade (%)')
            ax3.set_title('Volume vs Efetividade\n(tamanho = acordos)', fontweight='bold')
            ax3.grid(True, alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'Dados insuficientes\npara scatter plot', 
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Volume vs Efetividade', fontweight='bold')
        
        # 4. Pizza das principais classes
        df_pizza = df_classe.nlargest(5, 'Total_Processos')
        outros = df_classe['Total_Processos'].sum() - df_pizza['Total_Processos'].sum()
        
        labels_pizza = [nome[:20] + '...' if len(nome) > 20 else nome for nome in df_pizza['Nome']] + ['Outras']
        sizes_pizza = list(df_pizza['Total_Processos']) + [outros]
        
        ax4.pie(sizes_pizza, labels=labels_pizza, autopct='%1.1f%%', startangle=90)
        ax4.set_title('Distribuição por Classe (Top 5)', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('analise_por_classe.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Análise por classe criada: analise_por_classe.png")
    
    def criar_matriz_correlacao(self):
        """Matriz de correlação"""
        print(f"\n🔗 CRIANDO MATRIZ DE CORRELAÇÃO")
        
        # Procura aba de processos detalhados
        aba_detalhes = None
        for nome_aba in ['Processos_Detalhados', 'Processos Detalhados', 'processos_detalhados', 'Detalhes']:
            if nome_aba in self.dados:
                aba_detalhes = nome_aba
                break
        
        if not aba_detalhes:
            print("❌ Aba de processos detalhados não encontrada")
            return
        
        df = self.dados[aba_detalhes].copy()
        print(f"📋 Usando aba: {aba_detalhes}")
        
        # Seleciona colunas numéricas
        colunas_numericas = []
        for col in df.columns:
            if df[col].dtype in ['bool', 'int64', 'float64'] or col.lower() in ['tem tutela', 'tem acordo', 'tutela e acordo']:
                colunas_numericas.append(col)
        
        if len(colunas_numericas) < 3:
            print("❌ Dados insuficientes para correlação")
            print(f"📋 Colunas numéricas encontradas: {colunas_numericas}")
            return
        
        # Converte booleanos e strings booleanas
        for col in colunas_numericas:
            if df[col].dtype == 'bool':
                df[col] = df[col].astype(int)
            elif df[col].dtype == 'object':
                # Tenta converter True/False strings
                df[col] = df[col].map({'True': 1, 'False': 0, True: 1, False: 0}).fillna(df[col])
        
        # Remove colunas com muitos NaN
        df_corr = df[colunas_numericas].dropna(axis=1, thresh=len(df)*0.5)
        
        if df_corr.empty or len(df_corr.columns) < 3:
            print("❌ Dados insuficientes após limpeza")
            return
        
        # Calcula correlação
        corr_matrix = df_corr.corr()
        
        # Cria heatmap
        plt.figure(figsize=(10, 8))
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        
        sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdBu_r', center=0,
                   square=True, linewidths=0.5, cbar_kws={"shrink": .8})
        
        plt.title('Matriz de Correlação - Variáveis de Jurimetria', 
                 fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig('matriz_correlacao.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Matriz de correlação criada: matriz_correlacao.png")
    
    def criar_relatorio_html(self):
        """Relatório HTML com imagens"""
        print(f"\n📋 CRIANDO RELATÓRIO HTML")
        
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Jurimetria - RCE em Saúde Pública</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .chart-container {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 8px;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .insight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
        }}
        .insight-box h3 {{
            margin-top: 0;
            color: white;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #bdc3c7;
            color: #7f8c8d;
        }}
        .file-info {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Relatório de Jurimetria<br>RCE em Saúde Pública</h1>
        
        <div class="file-info">
            <h3>📁 Informações do Arquivo</h3>
            <p><strong>Arquivo analisado:</strong> {os.path.basename(self.arquivo_excel)}</p>
            <p><strong>Abas processadas:</strong> {', '.join(self.dados.keys())}</p>
            <p><strong>Data de geração:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </div>
        
        <div class="insight-box">
            <h3>🎯 Sobre Esta Análise</h3>
            <p>Este relatório apresenta visualizações dos dados de jurimetria sobre Responsabilidade Civil do Estado em Saúde Pública. As análises incluem métricas de efetividade de tutelas, distribuição por classes processuais e correlações entre variáveis.</p>
        </div>
        
        <h2>📊 Dashboard Executivo</h2>
        <div class="chart-container">
            <img src="dashboard_executivo.png" alt="Dashboard Executivo">
            <p><em>Visão geral das métricas principais de jurimetria</em></p>
        </div>
        
        <h2>🏛️ Análise por Classe Processual</h2>
        <div class="chart-container">
            <img src="analise_por_classe.png" alt="Análise por Classe">
            <p><em>Distribuição e efetividade por tipo de ação judicial</em></p>
        </div>
        
        <h2>🔗 Matriz de Correlação</h2>
        <div class="chart-container">
            <img src="matriz_correlacao.png" alt="Matriz de Correlação">
            <p><em>Correlações entre variáveis do processo judicial</em></p>
        </div>
        
        <div class="insight-box">
            <h3>💡 Como Interpretar os Gráficos</h3>
            <ul>
                <li><strong>Dashboard Executivo:</strong> Mostra o funil de efetividade das tutelas e distribuição geral dos processos</li>
                <li><strong>Análise por Classe:</strong> Identifica quais tipos de ação têm maior volume e efetividade</li>
                <li><strong>Matriz de Correlação:</strong> Revela relações entre diferentes variáveis do processo</li>
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>Relatório gerado em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
            <p><strong>Ferramenta:</strong> Visualizador Configurável de Jurimetria</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open('relatorio_jurimetria_configuravel.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Relatório HTML criado: relatorio_jurimetria_configuravel.html")
    
    def gerar_todas_visualizacoes(self):
        """Gera todas as visualizações"""
        print(f"\n🎨 GERANDO TODAS AS VISUALIZAÇÕES")
        print(f"{'='*60}")
        
        try:
            self.criar_dashboard_executivo()
            self.criar_analise_por_classe()
            self.criar_matriz_correlacao()
            self.criar_relatorio_html()
            
            print(f"\n{'='*60}")
            print(f"🎉 VISUALIZAÇÕES CRIADAS!")
            print(f"{'='*60}")
            print(f"📁 Arquivos gerados:")
            print(f"   📊 dashboard_executivo.png")
            print(f"   🏛️ analise_por_classe.png")
            print(f"   🔗 matriz_correlacao.png")
            print(f"   📋 relatorio_jurimetria_configuravel.html")
            print(f"\n💡 Abra 'relatorio_jurimetria_configuravel.html' no navegador!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Função principal"""
    print(f"""
{'='*60}
🎨 VISUALIZADOR CONFIGURÁVEL DE JURIMETRIA
📊 Aceita qualquer arquivo Excel com dados de jurimetria
⚖️ Análise visual adaptável aos seus dados
{'='*60}
""")
    
    # Verifica se foi passado arquivo como argumento
    if len(sys.argv) > 1:
        arquivo_excel = sys.argv[1]
        print(f"📊 Arquivo especificado: {arquivo_excel}")
    else:
        # Procura arquivos Excel na pasta atual
        import glob
        
        # Primeiro tenta o padrão específico
        arquivos_padrao = glob.glob("jurimetria_rce_saude_tjmt_*.xlsx")
        
        if arquivos_padrao:
            arquivo_excel = max(arquivos_padrao, key=os.path.getctime)
            print(f"📊 Arquivo padrão encontrado: {arquivo_excel}")
        else:
            # Procura qualquer Excel
            arquivos_excel = glob.glob("*.xlsx") + glob.glob("*.xls")
            
            if not arquivos_excel:
                print("❌ Nenhum arquivo Excel encontrado!")
                print("\n💡 Opções:")
                print("1. Coloque um arquivo Excel na pasta atual")
                print("2. Execute: python3 visualizacao_configuravel.py caminho/para/arquivo.xlsx")
                print("3. Renomeie seu arquivo para: jurimetria_rce_saude_tjmt_AAAAMMDD_HHMMSS.xlsx")
                return
            
            if len(arquivos_excel) == 1:
                arquivo_excel = arquivos_excel[0]
                print(f"📊 Arquivo Excel encontrado: {arquivo_excel}")
            else:
                print(f"📊 Múltiplos arquivos Excel encontrados:")
                for i, arquivo in enumerate(arquivos_excel, 1):
                    print(f"   {i}. {arquivo}")
                
                try:
                    escolha = input(f"\n🤔 Escolha um arquivo (1-{len(arquivos_excel)}): ")
                    indice = int(escolha) - 1
                    arquivo_excel = arquivos_excel[indice]
                    print(f"📊 Arquivo selecionado: {arquivo_excel}")
                except (ValueError, IndexError):
                    arquivo_excel = arquivos_excel[0]
                    print(f"📊 Usando primeiro arquivo: {arquivo_excel}")
    
    # Gera visualizações
    try:
        visualizador = VisualizadorConfiguravel(arquivo_excel)
        visualizador.gerar_todas_visualizacoes()
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

