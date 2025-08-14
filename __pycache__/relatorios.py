# Adicione esta importação no início do app.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from tkinter import messagebox

# Importe ou defina o objeto database antes de usar
from database import database  # Certifique-se de que existe um módulo database.py com o objeto database definido

def formatar_data_para_exibicao(data_str):
    """Formata uma data no formato YYYY-MM-DD para DD/MM/YYYY."""
    from datetime import datetime
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return data_str

def gerar_relatorio_sessao_pdf(sessao_id):
    """Gera um relatório em PDF para uma sessão específica."""
    try:
        # 1. Buscar os dados
        sessao_data = database.buscar_sessao_por_id(sessao_id)
        # Precisamos do ID do paciente para buscar seus dados.
        # (Esta parte exigiria uma pequena alteração em `buscar_sessao_por_id` para retornar também o paciente_id e nome)
        # Por simplicidade, vamos assumir que temos os dados.
        
        paciente_nome = "Nome do Paciente (Exemplo)" # Substituir com dados reais
        data_sessao = formatar_data_para_exibicao(sessao_data.get('data_sessao'))
        
        nome_arquivo = f"relatorio_sessao_{sessao_id}_{paciente_nome.replace(' ', '_')}.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=letter)
        width, height = letter # (612, 792)

        # 2. Escrever o conteúdo
        c.setFont("Helvetica-Bold", 16)
        c.drawString(inch, height - inch, "Relatório de Sessão Terapêutica")

        c.setFont("Helvetica", 12)
        c.drawString(inch, height - 1.5*inch, f"Paciente: {paciente_nome}")
        c.drawString(inch, height - 1.7*inch, f"Data da Sessão: {data_sessao}")

        # Adicionar mais detalhes da sessão...
        # ... resumo, evolução, plano, etc.

        # 3. Salvar o PDF
        c.save()
        messagebox.showinfo("Sucesso", f"Relatório salvo como '{nome_arquivo}'")

    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível gerar o PDF: {e}")

