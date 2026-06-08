import pdfplumber
import pandas as pd
import re
from datetime import datetime
import json
import os
from typing import Dict, List, Any, Optional
from collections import Counter

class ExtratorExtratosBancarios:
    """
    Classe para extrair e processar extratos bancários de PDFs
    Com categorização automática de despesas
    """
    
    def __init__(self):
        # Dicionário de categorias com palavras-chave
        self.categorias = {
            'Alimentação': [
                'supermercado', 'continente', 'pingo doce', 'lidl', 'aldi', 'mercado',
                'restaurante', 'cafe', 'pastelaria', 'padaria', 'auchan', 'el corte',
                'comida', 'mercearia', 'frutaria', 'talho', 'peixaria'
            ],
            'Transporte': [
                'uber', 'bolt', 'taxi', 'cp', 'comboios', 'metro', 'carris',
                'transportes', 'gasolina', 'galp', 'bp', 'repsol', 'prio', 'cepsa',
                'estacionamento', 'parque', 'portagem', 'scut', 'via verde',
                'oficina', 'mecanico', 'pneus', 'revisao', 'manutencao'
            ],
            'Habitação': [
                'renda', 'condominio', 'eletricidade', 'edp', 'endesa', 'goldenergy',
                'agua', 'epal', 'indaqua', 'gas', 'galp energia', 'meo', 'nos',
                'vodafone', 'internet', 'tv', 'telefone', 'imposto', 'imi', 'municipe'
            ],
            'Saúde': [
                'farmácia', 'farmacia', 'medico', 'consulta', 'hospital', 'clinica',
                'dentista', 'enfermagem', 'exames', 'analises', 'seguro saude',
                'medicare', 'advancecare', 'multicare'
            ],
            'Educação': [
                'escola', 'universidade', 'faculdade', 'propina', 'livro', 'material',
                'curso', 'formacao', 'workshop', 'explicacoes', 'aulas'
            ],
            'Lazer': [
                'cinema', 'teatro', 'concerto', 'espetaculo', 'bilhete', 'ingresso',
                'netflix', 'spotify', 'disney', 'hbo', 'amazon prime', 'gaming',
                'playstation', 'xbox', 'steam', 'jogo'
            ],
            'Vestuário': [
                'roupa', 'calcado', 'sapato', 'camisa', 'calca', 'vestido',
                'zara', 'hm', 'bershka', 'pull and bear', 'mango', 'c&a', 'primark',
                'loja de roupa', 'moda'
            ],
            'Supermercado': [
                'continente', 'pingo doce', 'lidli', 'aldi', 'froiz',
                'mercadona', 'intermache', 'auchan'
            ],
            'Serviços': [
                'seguro', 'banco', 'comissao', 'manutencao', 'advogado', 'contabilista',
                'limpeza', 'jardim', 'piscina', 'eletricista', 'canalizador'
            ],
            'Impostos': [
                'irs', 'iva', 'imposto', 'financas', 'seguranca social', 'ss',
                'câmara municipal', 'fisco'
            ],
            'Investimentos': [
                'degiro', 'etoro', 'binance', 'coinbase', 'bitcoin', 'acao', 'fundo',
                'corretora', 'trading', 'reforma', 'ppr'
            ],
            'Animais': [
                'veterinario', 'pet', 'cão', 'gato', 'ração', 'tosa', 'animal',
                'clinica veterinaria', 'pet shop'
            ],
            'Presentes': [
                'casamento', 'aniversario', 'oferta', 'lembranca', 'brinquedo'
            ],
            'Outros': []  # Categoria padrão
        }
        
        # Adicionar sinónimos e variações
        self._expandir_categorias()
        
        # Padrões bancários
        self.padroes_bancos = {
            'CGD': {'data_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})', 'encoding': 'latin1'},
            'BCP': {'data_pattern': r'(\d{4}[/-]\d{2}[/-]\d{2})', 'encoding': 'utf-8'},
            'Novo Banco': {'data_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})', 'encoding': 'utf-8'},
            'Santander': {'data_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})', 'encoding': 'latin1'},
            'BPI': {'data_pattern': r'(\d{2}[/-]\d{2}[/-]\d{4})', 'encoding': 'utf-8'}
        }
        
        # Histórico de categorizações para aprendizado
        self.historico_categorias = {}
    
    def _expandir_categorias(self):
        """Expande as categorias com sinónimos e variações"""
        variacoes = {
            'alimentação': ['alimentacao', 'comida', 'refeicao', 'jantar', 'almoco'],
            'transporte': ['transportes', 'viagem', 'deslocamento'],
            'habitação': ['habitacao', 'casa', 'moradia'],
            'lazer': ['entretenimento', 'diversao', 'hobby']
        }
        
        for categoria, sinônimos in variacoes.items():
            for cat, palavras in self.categorias.items():
                if cat.lower() == categoria:
                    self.categorias[cat].extend(sinônimos)
    
    def extrair_texto_pdf(self, caminho_pdf: str) -> str:
        """Extrai texto bruto do PDF"""
        texto_completo = ""
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo += texto + "\n"
            return texto_completo
        except Exception as e:
            print(f"Erro ao ler PDF: {e}")
            return ""
    
    def extrair_tabelas_pdf(self, caminho_pdf: str) -> List[pd.DataFrame]:
        """Extrai tabelas diretamente do PDF"""
        tabelas = []
        try:
            with pdfplumber.open(caminho_pdf) as pdf:
                for pagina in pdf.pages:
                    tabelas_pagina = pagina.extract_tables()
                    for tabela in tabelas_pagina:
                        if tabela and len(tabela) > 1:
                            df = pd.DataFrame(tabela[1:], columns=tabela[0])
                            tabelas.append(df)
            return tabelas
        except Exception as e:
            print(f"Erro ao extrair tabelas: {e}")
            return []
    
    def identificar_banco(self, texto: str) -> str:
        """Identifica o banco baseado no texto do extrato"""
        bancos = {
            'CGD': ['caixa geral', 'cgd', 'caixadirecta'],
            'BCP': ['millennium', 'bcp', 'millennium bcp'],
            'Novo Banco': ['novo banco', 'nb'],
            'Santander': ['santander', 'santander totta'],
            'BPI': ['bpi', 'banco bpi']
        }
        
        texto_lower = texto.lower()
        for banco, palavras in bancos.items():
            for palavra in palavras:
                if palavra in texto_lower:
                    return banco
        return "Desconhecido"
    
    def categorizar_transacao(self, descricao: str) -> Dict[str, Any]:
        """
        Categoriza uma transação baseado na descrição
        Retorna categoria e confiança
        """
        descricao_lower = descricao.lower()
        pontuacoes = {}
        
        for categoria, palavras in self.categorias.items():
            pontuacao = 0
            palavras_encontradas = []
            
            for palavra in palavras:
                if palavra in descricao_lower:
                    # Palavras mais específicas valem mais pontos
                    peso = len(palavra) / 10  # Palavras mais longas = mais específicas
                    pontuacao += 1 + peso
                    palavras_encontradas.append(palavra)
            
            if pontuacao > 0:
                pontuacoes[categoria] = {
                    'pontuacao': pontuacao,
                    'palavras': palavras_encontradas
                }
        
        if pontuacoes:
            # Escolhe categoria com maior pontuação
            melhor_categoria = max(pontuacoes.items(), key=lambda x: x[1]['pontuacao'])
            return {
                'categoria': melhor_categoria[0],
                'confianca': min(1.0, melhor_categoria[1]['pontuacao'] / 5),
                'palavras_chave': melhor_categoria[1]['palavras']
            }
        
        return {'categoria': 'Outros', 'confianca': 0.3, 'palavras_chave': []}
    
    def extrair_transacoes_regex(self, texto: str) -> List[Dict]:
        """Extrai transações usando expressões regulares e categoriza"""
        transacoes = []
        padrao_data = r'(\d{2}[/-]\d{2}[/-]\d{4})'
        padrao_valor = r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})'
        
        linhas = texto.split('\n')
        
        for i, linha in enumerate(linhas):
            match_data = re.search(padrao_data, linha)
            
            if match_data:
                data = match_data.group(1)
                valores = re.findall(padrao_valor, linha)
                resto = linha[match_data.end():].strip()
                
                descricao = resto
                debito = 0
                credito = 0
                
                if valores:
                    for valor in valores:
                        descricao = descricao.replace(valor, '').strip()
                    
                    if len(valores) == 1:
                        if 'débito' in linha.lower() or 'debito' in linha.lower():
                            debito = self._converter_valor(valores[0])
                        else:
                            credito = self._converter_valor(valores[0])
                    elif len(valores) >= 2:
                        debito = self._converter_valor(valores[0])
                        credito = self._converter_valor(valores[1])
                
                if descricao and (debito > 0 or credito > 0):
                    # Categorizar automaticamente
                    categoria_info = self.categorizar_transacao(descricao)
                    
                    transacoes.append({
                        'data': data,
                        'descricao': descricao,
                        'debito': debito,
                        'credito': credito,
                        'saldo': 0,
                        'categoria': categoria_info['categoria'],
                        'confianca_categoria': categoria_info['confianca'],
                        'palavras_chave': categoria_info['palavras_chave']
                    })
        
        return transacoes
    
    def _converter_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        valor_limpo = valor_str.replace(' ', '').replace(',', '.')
        valor_limpo = re.sub(r'[^\d.-]', '', valor_limpo)
        try:
            return float(valor_limpo)
        except:
            return 0.0
    
    def processar_extrato(self, caminho_pdf: str) -> Dict[str, Any]:
        """Processa o extrato completo com categorização"""
        
        print(f"📄 Processando: {caminho_pdf}")
        
        texto = self.extrair_texto_pdf(caminho_pdf)
        if not texto:
            return {"erro": "Não foi possível extrair texto do PDF"}
        
        banco = self.identificar_banco(texto)
        print(f"🏦 Banco identificado: {banco}")
        
        transacoes = self.extrair_transacoes_regex(texto)
        
        if not transacoes:
            print("Tentando extrair tabelas...")
            tabelas = self.extrair_tabelas_pdf(caminho_pdf)
            if tabelas:
                transacoes = self._converter_tabela_para_transacoes(tabelas[0])
        
        if transacoes:
            saldo_acumulado = 0
            for transacao in transacoes:
                saldo_acumulado += transacao['credito'] - transacao['debito']
                transacao['saldo'] = saldo_acumulado
        
        # Estatísticas por categoria
        stats_categorias = self._estatisticas_por_categoria(transacoes)
        
        resultado = {
            'banco': banco,
            'data_processamento': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_transacoes': len(transacoes),
            'total_debitos': sum(t['debito'] for t in transacoes),
            'total_creditos': sum(t['credito'] for t in transacoes),
            'saldo_final': sum(t['credito'] - t['debito'] for t in transacoes),
            'stats_categorias': stats_categorias,
            'transacoes': transacoes
        }
        
        return resultado
    
    def _estatisticas_por_categoria(self, transacoes: List[Dict]) -> Dict:
        """Calcula estatísticas agregadas por categoria"""
        stats = {}
        
        for transacao in transacoes:
            categoria = transacao['categoria']
            valor_gasto = transacao['debito']
            valor_recebido = transacao['credito']
            
            if categoria not in stats:
                stats[categoria] = {
                    'total_gasto': 0,
                    'total_recebido': 0,
                    'num_transacoes': 0,
                    'confianca_media': 0
                }
            
            stats[categoria]['total_gasto'] += valor_gasto
            stats[categoria]['total_recebido'] += valor_recebido
            stats[categoria]['num_transacoes'] += 1
            stats[categoria]['confianca_media'] += transacao['confianca_categoria']
        
        # Calcular médias
        for categoria in stats:
            stats[categoria]['confianca_media'] /= stats[categoria]['num_transacoes']
        
        return stats
    
    def _converter_tabela_para_transacoes(self, df: pd.DataFrame) -> List[Dict]:
        """Converte DataFrame de tabela para lista de transações com categorização"""
        transacoes = []
        
        colunas = {col.lower(): col for col in df.columns}
        
        col_data = None
        col_desc = None
        col_debito = None
        col_credito = None
        
        for col, col_original in colunas.items():
            if any(p in col for p in ['data', 'date', 'mov']):
                col_data = col_original
            elif any(p in col for p in ['descri', 'description', 'texto', 'movimento']):
                col_desc = col_original
            elif any(p in col for p in ['débito', 'debito', 'debt', 'gasto', 'despesa']):
                col_debito = col_original
            elif any(p in col for p in ['crédito', 'credito', 'credit', 'receita', 'income']):
                col_credito = col_original
        
        if col_data:
            for _, row in df.iterrows():
                descricao = str(row[col_desc]) if col_desc and pd.notna(row[col_desc]) else ''
                
                if descricao and descricao != 'nan':
                    categoria_info = self.categorizar_transacao(descricao)
                    
                    transacao = {
                        'data': str(row[col_data]) if col_data and pd.notna(row[col_data]) else '',
                        'descricao': descricao,
                        'debito': float(row[col_debito]) if col_debito and pd.notna(row[col_debito]) else 0,
                        'credito': float(row[col_credito]) if col_credito and pd.notna(row[col_credito]) else 0,
                        'saldo': 0,
                        'categoria': categoria_info['categoria'],
                        'confianca_categoria': categoria_info['confianca'],
                        'palavras_chave': categoria_info['palavras_chave']
                    }
                    
                    if transacao['debito'] > 0 or transacao['credito'] > 0:
                        transacoes.append(transacao)
        
        return transacoes
    
    def exportar_csv(self, resultado: Dict, caminho_saida: str):
        """Exporta transações para CSV"""
        if 'transacoes' in resultado and resultado['transacoes']:
            df = pd.DataFrame(resultado['transacoes'])
            df.to_csv(caminho_saida, index=False, encoding='utf-8-sig')
            print(f"✅ CSV exportado: {caminho_saida}")
        else:
            print("⚠️ Nenhuma transação para exportar")
    
    def exportar_json(self, resultado: Dict, caminho_saida: str):
        """Exporta resultado completo para JSON"""
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ JSON exportado: {caminho_saida}")
    
    def exportar_excel(self, resultado: Dict, caminho_saida: str):
        """Exporta transações para Excel com múltiplas abas"""
        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            # Aba de transações
            if resultado['transacoes']:
                df_transacoes = pd.DataFrame(resultado['transacoes'])
                df_transacoes.to_excel(writer, sheet_name='Transações', index=False)
            
            # Aba de resumo
            df_resumo = pd.DataFrame([{
                'Banco': resultado['banco'],
                'Data Processamento': resultado['data_processamento'],
                'Total Transações': resultado['total_transacoes'],
                'Total Débitos': resultado['total_debitos'],
                'Total Créditos': resultado['total_creditos'],
                'Saldo Final': resultado['saldo_final']
            }])
            df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
            
            # Aba de estatísticas por categoria
            if 'stats_categorias' in resultado:
                df_stats = pd.DataFrame(resultado['stats_categorias']).T
                df_stats = df_stats.reset_index().rename(columns={'index': 'Categoria'})
                df_stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        print(f"✅ Excel exportado: {caminho_saida}")
    
    def exibir_resumo(self, resultado: Dict):
        """Exibe resumo formatado com categorias"""
        print("\n" + "="*70)
        print(f"📊 RESUMO DO EXTRATO")
        print("="*70)
        print(f"🏦 Banco: {resultado['banco']}")
        print(f"📅 Processado em: {resultado['data_processamento']}")
        print(f"📝 Total de transações: {resultado['total_transacoes']}")
        print(f"💰 Total de débitos: €{resultado['total_debitos']:.2f}")
        print(f"💳 Total de créditos: €{resultado['total_creditos']:.2f}")
        print(f"⚖️ Saldo final: €{resultado['saldo_final']:.2f}")
        
        # Estatísticas por categoria
        if 'stats_categorias' in resultado and resultado['stats_categorias']:
            print("\n" + "="*70)
            print("📊 GASTOS POR CATEGORIA")
            print("="*70)
            
            # Ordenar por total gasto
            categorias_ordenadas = sorted(
                resultado['stats_categorias'].items(),
                key=lambda x: x[1]['total_gasto'],
                reverse=True
            )
            
            for categoria, stats in categorias_ordenadas:
                if stats['total_gasto'] > 0:
                    percentual = (stats['total_gasto'] / resultado['total_debitos']) * 100 if resultado['total_debitos'] > 0 else 0
                    barra = "█" * int(percentual / 2)  # Barra visual
                    print(f"\n📌 {categoria}:")
                    print(f"   💸 Gasto: €{stats['total_gasto']:.2f} ({percentual:.1f}%) {barra}")
                    print(f"   📈 Recebido: €{stats['total_recebido']:.2f}")
                    print(f"   🔢 Transações: {stats['num_transacoes']}")
                    print(f"   ⚡ Confiança média: {stats['confianca_media']:.1%}")
        
        # Últimas transações
        if resultado['transacoes']:
            print("\n" + "="*70)
            print("📋 ÚLTIMAS 10 TRANSAÇÕES")
            print("="*70)
            for transacao in resultado['transacoes'][-10:]:
                tipo = "💸 Débito" if transacao['debito'] > 0 else "💰 Crédito"
                valor = transacao['debito'] if transacao['debito'] > 0 else transacao['credito']
                confianca = "✓" if transacao['confianca_categoria'] > 0.7 else "?"
                
                print(f"{transacao['data']} | {tipo}: €{valor:.2f} | "
                      f"[{transacao['categoria']}] {confianca}")
                print(f"   📝 {transacao['descricao'][:60]}")
                if transacao['palavras_chave']:
                    print(f"   🔑 Palavras-chave: {', '.join(transacao['palavras_chave'][:3])}")
                print()
        
        print("="*70)
    
    def aprender_categoria(self, descricao: str, categoria_correta: str):
        """Permite ao usuário corrigir categorias e aprender com isso"""
        if categoria_correta not in self.categorias:
            self.categorias[categoria_correta] = []
        
        # Extrair palavras-chave da descrição
        palavras = re.findall(r'\b[a-záàâãçéêíóôõúü]{3,}\b', descricao.lower())
        
        # Adicionar ao dicionário de categorias
        for palavra in palavras:
            if palavra not in self.categorias[categoria_correta]:
                self.categorias[categoria_correta].append(palavra)
        
        print(f"✅ Aprendido: '{descricao[:50]}...' → {categoria_correta}")
    
    def salvar_categorias(self, arquivo: str = "categorias_personalizadas.json"):
        """Salva as categorias personalizadas para uso futuro"""
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.categorias, f, indent=2, ensure_ascii=False)
        print(f"✅ Categorias salvas em: {arquivo}")
    
    def carregar_categorias(self, arquivo: str = "categorias_personalizadas.json"):
        """Carrega categorias previamente salvas"""
        if os.path.exists(arquivo):
            with open(arquivo, 'r', encoding='utf-8') as f:
                categorias_carregadas = json.load(f)
                self.categorias.update(categorias_carregadas)
            print(f"✅ Categorias carregadas de: {arquivo}")
        else:
            print(f"⚠️ Arquivo {arquivo} não encontrado")

# Interface interativa melhorada
def main_interativa():
    """Versão interativa com opções de aprendizado"""
    print("🔄 CONVERSOR DE EXTRATOS BANCÁRIOS COM CATEGORIZAÇÃO")
    print("="*60)
    
    extrator = ExtratorExtratosBancarios()
    
    # Carregar categorias salvas anteriormente
    extrator.carregar_categorias()
    
    while True:
        print("\n📁 OPÇÕES:")
        print("1 - Processar novo extrato")
        print("2 - Ver/editar categorias")
        print("3 - Salvar categorias personalizadas")
        print("4 - Sair")
        
        opcao = input("\nEscolha uma opção (1-4): ").strip()
        
        if opcao == "1":
            caminho = input("Digite o caminho do PDF do extrato: ").strip()
            
            if os.path.exists(caminho):
                resultado = extrator.processar_extrato(caminho)
                
                if "erro" not in resultado:
                    extrator.exibir_resumo(resultado)
                    
                    # Perguntar formatos de exportação
                    print("\n📁 Formatos disponíveis:")
                    print("1 - CSV")
                    print("2 - JSON")
                    print("3 - Excel")
                    print("4 - Todos")
                    print("5 - Apenas ver resumo")
                    
                    formato = input("Escolha o formato (1-5): ").strip()
                    
                    nome_base = os.path.splitext(caminho)[0]
                    
                    if formato in ['1', '4']:
                        extrator.exportar_csv(resultado, f"{nome_base}_categorizado.csv")
                    if formato in ['2', '4']:
                        extrator.exportar_json(resultado, f"{nome_base}_categorizado.json")
                    if formato in ['3', '4']:
                        extrator.exportar_excel(resultado, f"{nome_base}_categorizado.xlsx")
                    
                    # Opção de corrigir categorias
                    corrigir = input("\nDeseja corrigir alguma categoria? (s/n): ").lower()
                    if corrigir == 's':
                        print("\n📝 Transações com baixa confiança:")
                        transacoes_baixa = [t for t in resultado['transacoes'] 
                                          if t['confianca_categoria'] < 0.7]
                        
                        for transacao in transacoes_baixa[:10]:  # Mostrar até 10
                            print(f"\n📌 {transacao['descricao'][:80]}")
                            print(f"   Categoria atual: {transacao['categoria']} "
                                  f"(confiança: {transacao['confianca_categoria']:.1%})")
                            
                            nova_cat = input("   Nova categoria (Enter para manter, 'skip' para pular): ").strip()
                            if nova_cat and nova_cat != 'skip':
                                extrator.aprender_categoria(transacao['descricao'], nova_cat)
                else:
                    print(f"❌ Erro: {resultado['erro']}")
            else:
                print("❌ Arquivo não encontrado!")
        
        elif opcao == "2":
            print("\n📚 CATEGORIAS ATUAIS:")
            for categoria, palavras in extrator.categorias.items():
                if palavras:  # Mostrar apenas categorias com palavras
                    print(f"\n🔹 {categoria}:")
                    print(f"   {', '.join(palavras[:10])}")
                    if len(palavras) > 10:
                        print(f"   ... e mais {len(palavras)-10} palavras")
        
        elif opcao == "3":
            extrator.salvar_categorias()
        
        elif opcao == "4":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida!")

# Exemplo de uso simples
def exemplo_rapido():
    """Exemplo rápido de uso"""
    extrator = ExtratorExtratosBancarios()
    
    # Processar um extrato (substitua pelo seu arquivo)
    resultado = extrator.processar_extrato("extrato_bancario.pdf")
    
    if "erro" not in resultado:
        # Exportar para Excel (melhor formato para análise)
        extrator.exportar_excel(resultado, "analise_financeira.xlsx")
        
        # Exibir resumo
        extrator.exibir_resumo(resultado)
        
        # Salvar categorias aprendidas
        extrator.salvar_categorias()
    else:
        print(f"Erro: {resultado['erro']}")

if __name__ == "__main__":
    # Executar interface interativa
    main_interativa()