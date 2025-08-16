import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Callable, Dict, Any
from datetime import date, datetime
import sqlite3
import database  # Importa nosso módulo de banco de dados
import calendar # Módulo para trabalhar com calendários mensais
from tkcalendar import Calendar # Importa o calendário
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

# Variável global para armazenar os dados do usuário logado
USUARIO_LOGADO = None

# --- Constantes e Dicionários Auxiliares ---
DIAS_SEMANA_MAP = {
    "Segunda-feira": 0, "Terça-feira": 1, "Quarta-feira": 2,
    "Quinta-feira": 3, "Sexta-feira": 4, "Sábado": 5, "Domingo": 6
}
DIAS_SEMANA_LISTA = list(DIAS_SEMANA_MAP.keys())
DIAS_SEMANA_INV_MAP = {v: k for k, v in DIAS_SEMANA_MAP.items()}

TERAPIAS_POR_NIVEL = {
    "Nível 1 – Apoio leve": """**Treinamento de Habilidades Sociais**
- Jogos de tabuleiro em grupo (aprender a esperar a vez).
- Simulações de situações do dia a dia (ex.: pedir algo em uma lanchonete).
- Dinâmicas de apresentações (falar sobre si para colegas).
- Exercícios de contato visual e cumprimento (aperto de mão, "oi", "tchau").

**Terapia Cognitivo-Comportamental (TCC)**
- Identificação de emoções em imagens.
- Diário de sentimentos (escrever ou desenhar como se sentiu).
- Treino de resolução de problemas simples ("O que você faria se…?").

**Fonoaudiologia**
- Jogos de rimas.
- Leitura compartilhada de histórias curtas.
- Atividades de entonação (ler frases mudando a emoção).

**Atividades Lúdicas**
- Jogos de memória.
- Desenho livre ou colorir.
- Música em grupo (cantar juntos, bater palmas no ritmo).""",
    "Nível 2 – Apoio moderado": """**Treinamento de Habilidades Sociais**
- Role play (ensaiar como pedir ajuda na escola).
- Dinâmicas em dupla (contar uma história junto).
- Atividades de cooperação (montar quebra-cabeça juntos).
- Jogo "passar a bola" para treinar interação.

**ABA**
- Treino de comunicação funcional (apontar figuras para pedir água).
- Reforço positivo (elogio ou prêmio por completar tarefa).
- Treino de autonomia (lavar as mãos sozinho, guardar brinquedos).

**Fonoaudiologia**
- Nomear objetos do cotidiano.
- Montar frases com figuras.
- Jogos de “o que é isso?” (mostrar e nomear).

**Terapia Ocupacional**
- Atividades de coordenação motora fina (botões, encaixar peças).
- Exercícios com texturas diferentes (areia, massinha, tecido).
- Treino de vestir roupas (colocar casaco, fechar zíper).

**Musicoterapia**
- Repetir sons e ritmos com instrumentos simples.
- Música de pergunta e resposta (“Eu canto uma frase e você responde”).
- Dança guiada em roda.""",
    "Nível 3 – Apoio intenso": """**Treinamento de Habilidades Sociais**
- Ensinar a pedir algo usando figuras ou tablet (PECS/CAA).
- Jogos simples de turnos (apertar botão na vez dele).
- Atividades de imitação (imitar gestos do terapeuta).
- Treino de rotina social (cumprimentar alguém com gesto).

**ABA intensiva**
- Reforço imediato por comportamento adequado.
- Sessões estruturadas de “sentar, olhar, apontar”.
- Pequenos passos de autonomia (guardar 1 brinquedo).
- Treino repetitivo com pausas curtas.

**Fonoaudiologia com CAA**
- Uso de cartões para expressar necessidades (água, comida, banheiro).
- Treino de sons básicos (vogais, sílabas repetidas).
- Comunicação com aplicativos no tablet.

**Terapia Ocupacional (Integração Sensorial)**
- Atividades com balanço ou bolas grandes (regular sensorialmente).
- Brincadeiras com massinha, espuma, água.
- Caminhar em tapetes de texturas.

**Equoterapia / Atividades alternativas**
- Montar no cavalo com apoio, estimulando equilíbrio.
- Carinho e cuidado com o animal.
- Passeios curtos guiados."""
}

# --- Funções Auxiliares ---

def formatar_data_para_db(data_str):
    """Converte data de DD/MM/YYYY para YYYY-MM-DD para salvar no DB."""
    if not data_str:
        return None
    try:
        # Converte para o formato do banco de dados, que permite ordenação correta
        return datetime.strptime(data_str, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        return None # Retorna None se o formato da data for inválido

def formatar_data_para_exibicao(data_str):
    """Converte data de YYYY-MM-DD para DD/MM/YYYY para exibir na UI."""
    if not data_str:
        return ""
    try:
        # Converte de volta para o formato amigável para o usuário
        return datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return data_str # Se já estiver em outro formato, retorna o original

def calcular_idade(data_nasc_db):
    """Calcula a idade a partir da data de nascimento no formato YYYY-MM-DD."""
    if not data_nasc_db:
        return ""
    try:
        nascimento = datetime.strptime(data_nasc_db, '%Y-%m-%d').date()
        hoje = date.today()
        # Calcula a idade de forma precisa
        idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        return idade
    except (ValueError, TypeError):
        return "" # Retorna vazio se a data for inválida

def _draw_wrapped_text(canvas_obj, text, x, y, max_width, max_height, style):
    """Função auxiliar para desenhar texto com quebra de linha em um canvas do ReportLab."""
    p = Paragraph(text.replace('\n', '<br/>'), style)
    w, h = p.wrapOn(canvas_obj, max_width, max_height)
    p.drawOn(canvas_obj, x, y - h)
    return y - h - 20  # Retorna a nova posição Y com um espaçamento

def gerar_relatorio_sessao_pdf(janela_pai, sessao_id):
    """Gera um relatório em PDF para uma sessão específica."""
    try:
        sessao_data = database.buscar_sessao_por_id(sessao_id)
        if not sessao_data:
            messagebox.showerror("Erro", "Não foi possível encontrar os dados da sessão.", parent=janela_pai)
            return

        paciente_nome_safe = "".join(c for c in sessao_data.get('paciente_nome', 'Paciente') if c.isalnum() or c in " ._").rstrip()
        nome_arquivo_sugerido = f"Relatorio_Sessao_{sessao_id}_{paciente_nome_safe}.pdf"
        
        nome_arquivo = filedialog.asksaveasfilename(
            initialfile=nome_arquivo_sugerido,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            parent=janela_pai
        )

        if not nome_arquivo:
            return

        c = canvas.Canvas(nome_arquivo, pagesize=letter)
        width, height = letter
        margin = inch

        styles = getSampleStyleSheet()
        style_h1 = styles['h1']
        style_h2 = styles['h2']
        style_body = styles['BodyText']
        
        y_pos = height - margin

        # Título e Informações Gerais
        y_pos = _draw_wrapped_text(c, "Relatório de Sessão Terapêutica", margin, y_pos, width - 2 * margin, height, style_h1)
        y_pos -= 10
        
        info_gerais = f"""
            <b>Paciente:</b> {sessao_data.get('paciente_nome', 'N/A')}<br/>
            <b>Data:</b> {formatar_data_para_exibicao(sessao_data.get('data_sessao'))}<br/>
            <b>Terapeuta:</b> {sessao_data.get('medico_nome', 'N/A')}
        """
        y_pos = _draw_wrapped_text(c, info_gerais, margin, y_pos, width - 2 * margin, height, style_body)

        # Seções do relatório
        y_pos = _draw_wrapped_text(c, "<b>Resumo da Sessão:</b>", margin, y_pos, width - 2 * margin, height, style_h2)
        y_pos = _draw_wrapped_text(c, sessao_data.get('resumo_sessao', 'Não informado.'), margin, y_pos, width - 2 * margin, height, style_body)
        y_pos = _draw_wrapped_text(c, "<b>Observações sobre a Evolução:</b>", margin, y_pos, width - 2 * margin, height, style_h2)
        y_pos = _draw_wrapped_text(c, sessao_data.get('observacoes_evolucao', 'Não informado.'), margin, y_pos, width - 2 * margin, height, style_body)
        y_pos = _draw_wrapped_text(c, "<b>Plano Terapêutico:</b>", margin, y_pos, width - 2 * margin, height, style_h2)
        _draw_wrapped_text(c, sessao_data.get('plano_terapeutico', 'Não informado.'), margin, y_pos, width - 2 * margin, height, style_body)
        
        c.save()
        messagebox.showinfo("Sucesso", f"Relatório salvo como '{nome_arquivo}'", parent=janela_pai)
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível gerar o PDF: {e}", parent=janela_pai)

def realizar_backup(janela_pai):
    """Abre uma caixa de diálogo para salvar um backup do banco de dados."""
    try:
        # Sugere um nome de arquivo com a data e hora atuais
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo_sugerido = f"backup_clinica_{timestamp}.db"
        
        backup_path = filedialog.asksaveasfilename(
            title="Salvar Backup Como",
            initialfile=nome_arquivo_sugerido,
            defaultextension=".db",
            filetypes=[("Arquivos de Banco de Dados", "*.db"), ("Todos os arquivos", "*.*")],
            parent=janela_pai
        )
        
        if backup_path:
            database.backup_database(backup_path)
            messagebox.showinfo("Backup Concluído", f"Backup salvo com sucesso em:\n{backup_path}", parent=janela_pai)
            
    except FileNotFoundError as e:
        messagebox.showerror("Erro", str(e), parent=janela_pai)
    except Exception as e:
        messagebox.showerror("Erro de Backup", f"Ocorreu um erro inesperado ao realizar o backup:\n{e}", parent=janela_pai)

def realizar_restauracao(janela_pai):
    """Abre uma caixa de diálogo para restaurar o banco de dados a partir de um backup."""
    aviso = "Atenção! A restauração substituirá TODOS os dados atuais por aqueles do arquivo de backup. Esta ação não pode ser desfeita.\n\nO aplicativo será fechado após a restauração. Deseja continuar?"
    if not messagebox.askyesno("Restauração de Dados", aviso, icon='warning', parent=janela_pai):
        return
        
    backup_path = filedialog.askopenfilename(title="Selecionar Arquivo de Backup para Restaurar", filetypes=[("Arquivos de Banco de Dados", "*.db"), ("Todos os arquivos", "*.*")], parent=janela_pai)
    if backup_path:
        try:
            database.restore_database(backup_path)
            messagebox.showinfo("Restauração Concluída", "O banco de dados foi restaurado com sucesso.\n\nO aplicativo será encerrado. Por favor, abra-o novamente.", parent=janela_pai)
            janela_pai.destroy()
        except FileNotFoundError as e:
            messagebox.showerror("Erro", str(e), parent=janela_pai)
        except Exception as e:
            messagebox.showerror("Erro de Restauração", f"Ocorreu um erro inesperado ao restaurar o banco de dados:\n{e}", parent=janela_pai)

def salvar_paciente(janela_cadastro, entry_nome, entry_data, entry_resp, entry_tel_resp, combo_plano, planos_map, entry_valor, text_terapias):
    """Coleta os dados dos campos de entrada e salva no banco de dados."""
    nome = entry_nome.get().strip()
    data_nasc_str = entry_data.get().strip()
    responsavel = entry_resp.get().strip()
    telefone_responsavel = entry_tel_resp.get().strip()
    nome_plano = combo_plano.get()
    valor_str = entry_valor.get().replace(',', '.').strip()
    anamnese_inicial = text_terapias.get("1.0", "end-1c").strip()

    if not nome or not data_nasc_str or not responsavel:
        messagebox.showerror("Erro de Validação", "Todos os campos são obrigatórios!", parent=janela_cadastro)
        return

    data_nasc_db = formatar_data_para_db(data_nasc_str)
    if not data_nasc_db:
        messagebox.showerror("Erro de Validação", "Formato de data inválido. Use DD/MM/AAAA.", parent=janela_cadastro)
        return

    try:
        plano_id = planos_map.get(nome_plano)
        valor_padrao = float(valor_str) if valor_str else 0.0
        database.adicionar_paciente(nome, data_nasc_db, responsavel, telefone_responsavel, plano_id, valor_padrao, anamnese_inicial)
        messagebox.showinfo("Sucesso", f"Paciente {nome} cadastrado com sucesso!", parent=janela_cadastro)
        janela_cadastro.destroy()
    except ValueError:
        messagebox.showerror("Erro de Validação", "O valor da sessão deve ser um número válido.", parent=janela_cadastro)
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar: {e}", parent=janela_cadastro)

def salvar_alteracoes_paciente(janela_edicao, entry_nome, entry_data, entry_resp, entry_tel_resp, combo_plano, planos_map, entry_valor, text_terapias, paciente_id):
    """Salva as alterações de um paciente existente."""
    nome = entry_nome.get().strip()
    data_nasc_str = entry_data.get().strip()
    responsavel = entry_resp.get().strip()
    telefone_responsavel = entry_tel_resp.get().strip()
    nome_plano = combo_plano.get()
    valor_str = entry_valor.get().replace(',', '.').strip()
    anamnese_texto = text_terapias.get("1.0", "end-1c").strip()

    if not nome or not data_nasc_str or not responsavel:
        messagebox.showerror("Erro de Validação", "Todos os campos são obrigatórios!", parent=janela_edicao)
        return

    data_nasc_db = formatar_data_para_db(data_nasc_str)
    if not data_nasc_db:
        messagebox.showerror("Erro de Validação", "Formato de data inválido. Use DD/MM/AAAA.", parent=janela_edicao)
        return

    try:
        plano_id = planos_map.get(nome_plano)
        valor_padrao = float(valor_str) if valor_str else 0.0
        database.atualizar_paciente(paciente_id, nome, data_nasc_db, responsavel, telefone_responsavel, plano_id, valor_padrao)
        database.atualizar_anamnese_paciente(paciente_id, anamnese_texto)
        messagebox.showinfo("Sucesso", "Dados do paciente atualizados com sucesso!", parent=janela_edicao)
        janela_edicao.destroy()
    except ValueError:
        messagebox.showerror("Erro de Validação", "O valor da sessão deve ser um número válido.", parent=janela_edicao)
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao atualizar: {e}", parent=janela_edicao)

def salvar_nova_sessao(janela_form, paciente_id, widgets):
    """Salva uma nova sessão no banco de dados."""
    try:
        data_sessao_str = widgets['data'].get().strip()
        hora_inicio = widgets['horario'].get().strip()
        hora_fim = widgets['hora_fim'].get().strip()
        nome_medico = widgets['combo_medico'].get()
        resumo = widgets['resumo'].get("1.0", "end-1c").strip()
        evolucao = widgets['evolucao'].get()
        obs_evolucao = widgets['obs_evolucao'].get("1.0", "end-1c").strip()
        plano = widgets['plano'].get("1.0", "end-1c").strip()

        if not data_sessao_str or not nome_medico:
            messagebox.showerror("Erro de Validação", "Os campos 'Data' e 'Terapeuta' são obrigatórios.", parent=janela_form)
            return

        data_sessao_db = formatar_data_para_db(data_sessao_str)
        if not data_sessao_db:
            messagebox.showerror("Erro de Validação", "Formato de data inválido. Use DD/MM/AAAA.", parent=janela_form)
            return

        # Obter o ID do médico a partir do nome selecionado
        medico_id = widgets['medico_map'].get(nome_medico)

        # --- VERIFICAÇÃO DE CONFLITO DE HORÁRIO ---
        sessoes_conflitantes = database.verificar_conflito_sessao(
            medico_id=medico_id, 
            data_db=data_sessao_db, 
            hora_inicio=hora_inicio, 
            hora_fim=hora_fim
        )
        if sessoes_conflitantes:
            messagebox.showwarning("Conflito de Horário", "O terapeuta já possui uma sessão agendada neste horário.", parent=janela_form)
            return

        # Validação do formato de hora
        try:
            if hora_inicio: datetime.strptime(hora_inicio, '%H:%M')
            if hora_fim: datetime.strptime(hora_fim, '%H:%M')
            if hora_inicio and hora_fim and datetime.strptime(hora_inicio, '%H:%M') >= datetime.strptime(hora_fim, '%H:%M'):
                messagebox.showwarning("Lógica Inválida", "O horário de início deve ser anterior ao de fim.", parent=janela_form)
                return
        except ValueError:
            messagebox.showerror("Formato Inválido", "O formato do horário deve ser HH:MM.", parent=janela_form)
            return

        database.adicionar_sessao(paciente_id, medico_id, data_sessao_db, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano)
        messagebox.showinfo("Sucesso", "Nova sessão registrada com sucesso!", parent=janela_form)
        janela_form.destroy()
    except KeyError as e:
        messagebox.showerror("Erro de Programação", f"Faltando widget no formulário: {e}", parent=janela_form)
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar a sessão: {e}", parent=janela_form)

def salvar_alteracoes_sessao(janela_form, sessao_id, widgets):
    """Salva as alterações de uma sessão existente."""
    try:
        data_sessao_str = widgets['data'].get().strip()
        hora_inicio = widgets['horario'].get().strip()
        hora_fim = widgets['hora_fim'].get().strip()
        nome_medico = widgets['combo_medico'].get()
        resumo = widgets['resumo'].get("1.0", "end-1c").strip()
        evolucao = widgets['evolucao'].get()
        obs_evolucao = widgets['obs_evolucao'].get("1.0", "end-1c").strip()
        plano = widgets['plano'].get("1.0", "end-1c").strip()

        if not data_sessao_str or not nome_medico:
            messagebox.showerror("Erro de Validação", "Os campos 'Data' e 'Terapeuta' são obrigatórios.", parent=janela_form)
            return

        data_sessao_db = formatar_data_para_db(data_sessao_str)
        if not data_sessao_db:
            messagebox.showerror("Erro de Validação", "Formato de data inválido. Use DD/MM/AAAA.", parent=janela_form)
            return

        # Obter o ID do médico a partir do nome selecionado
        medico_id = widgets['medico_map'].get(nome_medico)

        # --- VERIFICAÇÃO DE CONFLITO DE HORÁRIO (AO EDITAR) ---
        sessoes_conflitantes = database.verificar_conflito_sessao(
            medico_id=medico_id, 
            data_db=data_sessao_db, 
            hora_inicio=hora_inicio, 
            hora_fim=hora_fim,
            sessao_id_excluir=sessao_id # Ignora a própria sessão na verificação
        )
        if sessoes_conflitantes:
            messagebox.showwarning("Conflito de Horário", "O terapeuta já possui uma sessão agendada neste horário.", parent=janela_form)
            return

        # Validação do formato de hora
        try:
            if hora_inicio: datetime.strptime(hora_inicio, '%H:%M')
            if hora_fim: datetime.strptime(hora_fim, '%H:%M')
            if hora_inicio and hora_fim and datetime.strptime(hora_inicio, '%H:%M') >= datetime.strptime(hora_fim, '%H:%M'):
                messagebox.showwarning("Lógica Inválida", "O horário de início deve ser anterior ao de fim.", parent=janela_form)
                return
        except ValueError:
            messagebox.showerror("Formato Inválido", "O formato do horário deve ser HH:MM.", parent=janela_form)
            return

        database.atualizar_sessao(sessao_id, medico_id, data_sessao_db, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano)
        messagebox.showinfo("Sucesso", "Sessão atualizada com sucesso!", parent=janela_form)
        janela_form.destroy()
    except KeyError as e:
        messagebox.showerror("Erro de Programação", f"Faltando widget no formulário: {e}", parent=janela_form)
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar a sessão: {e}", parent=janela_form)


# --- Funções de Salvar/CRUD de Médicos ---

def salvar_medico(janela_cadastro, entry_nome, entry_espec, entry_contato):
    """Coleta os dados dos campos de entrada e salva um novo médico."""
    nome = entry_nome.get().strip()
    especialidade = entry_espec.get().strip()
    contato = entry_contato.get().strip()

    if not nome:
        messagebox.showerror("Erro de Validação", "O campo 'Nome Completo' é obrigatório!", parent=janela_cadastro)
        return

    try:
        database.adicionar_medico(nome, especialidade, contato)
        messagebox.showinfo("Sucesso", f"Médico(a) {nome} cadastrado(a) com sucesso!", parent=janela_cadastro)
        janela_cadastro.destroy()
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar: {e}", parent=janela_cadastro)

def salvar_alteracoes_medico(janela_edicao, entry_nome, entry_espec, entry_contato, medico_id):
    """Salva as alterações de um médico existente."""
    nome = entry_nome.get().strip()
    especialidade = entry_espec.get().strip()
    contato = entry_contato.get().strip()

    if not nome:
        messagebox.showerror("Erro de Validação", "O campo 'Nome Completo' é obrigatório!", parent=janela_edicao)
        return

    try:
        database.atualizar_medico(medico_id, nome, especialidade, contato)
        messagebox.showinfo("Sucesso", "Dados do médico atualizados com sucesso!", parent=janela_edicao)
        janela_edicao.destroy()
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao atualizar: {e}", parent=janela_edicao)

# --- Funções para Abrir Janelas de Médicos ---

def abrir_janela_form_medico(janela_pai, callback_atualizar, medico_id=None):
    """Abre uma janela de formulário para CRIAR ou EDITAR um médico/terapeuta."""
    is_edit_mode = medico_id is not None

    if is_edit_mode:
        medico_data = database.buscar_medico_por_id(medico_id)
        if not medico_data:
            messagebox.showerror("Erro", "Médico não encontrado.", parent=janela_pai)
            return
    
    janela_form = tk.Toplevel(janela_pai)
    janela_form.title("Editar Médico/Terapeuta" if is_edit_mode else "Cadastrar Novo Médico/Terapeuta")
    janela_form.geometry("400x200")
    janela_form.transient(janela_pai)
    janela_form.grab_set()

    frame = tk.Frame(janela_form, padx=20, pady=20)
    frame.pack(expand=True, fill='both')

    tk.Label(frame, text="Nome Completo:").grid(row=0, column=0, sticky="w", pady=5)
    entry_nome = tk.Entry(frame, width=40)
    entry_nome.grid(row=0, column=1, pady=5)
    entry_nome.focus_set()

    tk.Label(frame, text="Especialidade:").grid(row=1, column=0, sticky="w", pady=5)
    entry_espec = tk.Entry(frame, width=40)
    entry_espec.grid(row=1, column=1, pady=5)

    tk.Label(frame, text="Contato (Telefone/Email):").grid(row=2, column=0, sticky="w", pady=5)
    entry_contato = tk.Entry(frame, width=40)
    entry_contato.grid(row=2, column=1, pady=5)

    if is_edit_mode:
        entry_nome.insert(0, medico_data.get('nome_completo', ''))
        entry_espec.insert(0, medico_data.get('especialidade', '') or "")
        entry_contato.insert(0, medico_data.get('contato', '') or "")
        btn_text = "Salvar Alterações"
        save_command = lambda: salvar_alteracoes_medico(janela_form, entry_nome, entry_espec, entry_contato, medico_id)
    else:
        btn_text = "Salvar Cadastro"
        save_command = lambda: salvar_medico(janela_form, entry_nome, entry_espec, entry_contato)

    btn_salvar = tk.Button(frame, text=btn_text, command=save_command)
    btn_salvar.grid(row=3, column=1, sticky="e", pady=15)
    
    janela_pai.wait_window(janela_form)
    callback_atualizar()

def abrir_janela_disponibilidade(janela_pai, medico_id, medico_nome):
    """Abre uma janela com calendário para gerenciar a disponibilidade mensal de um médico."""
    janela_disp = tk.Toplevel(janela_pai)
    janela_disp.title(f"Agenda Mensal de {medico_nome}")
    janela_disp.geometry("900x550")
    janela_disp.transient(janela_pai)
    janela_disp.grab_set()

    # --- Frames Principais ---
    left_frame = ttk.Frame(janela_disp, padding=10)
    left_frame.pack(side='left', fill='y')
    right_frame = ttk.Frame(janela_disp, padding=10)
    right_frame.pack(side='right', fill='both', expand=True)

    # --- Calendário (Esquerda) ---
    hoje = date.today()
    cal = Calendar(left_frame, selectmode='day', year=hoje.year, month=hoje.month, day=hoje.day,
                   locale='pt_BR', date_pattern='dd/mm/y')
    cal.pack(pady=10)
    cal.tag_config('disponivel', background='lightgreen', foreground='black')

    # --- Detalhes do Dia (Direita) ---
    lbl_data_selecionada = ttk.Label(right_frame, text="Selecione um dia no calendário", font=("Helvetica", 12, "bold"))
    lbl_data_selecionada.pack(pady=(0, 10))

    # Tabela de horários
    tree_frame = ttk.Frame(right_frame)
    tree_frame.pack(fill='both', expand=True, pady=5)
    cols = ('ID', 'Início', 'Fim')
    tree_horarios = ttk.Treeview(tree_frame, columns=cols, show='headings')
    tree_horarios.heading('ID', text='ID'); tree_horarios.column('ID', width=0, stretch=tk.NO) # Oculto
    tree_horarios.heading('Início', text='Horário de Início'); tree_horarios.column('Início', anchor='center', width=100)
    tree_horarios.heading('Fim', text='Horário de Fim'); tree_horarios.column('Fim', anchor='center', width=100)
    tree_horarios.pack(side='left', fill='both', expand=True)
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_horarios.yview)
    tree_horarios.configure(yscroll=scrollbar.set); scrollbar.pack(side='right', fill='y')

    # Frame para adicionar novo horário
    add_frame = ttk.LabelFrame(right_frame, text="Adicionar Novo Horário", padding=10)
    add_frame.pack(fill='x', pady=10)
    ttk.Label(add_frame, text="Início (HH:MM):").grid(row=0, column=0, padx=5, pady=5)
    entry_inicio = ttk.Entry(add_frame, width=10)
    entry_inicio.grid(row=0, column=1, padx=5, pady=5)
    ttk.Label(add_frame, text="Fim (HH:MM):").grid(row=0, column=2, padx=5, pady=5)
    entry_fim = ttk.Entry(add_frame, width=10)
    entry_fim.grid(row=0, column=3, padx=5, pady=5)

    def marcar_dias_disponiveis():
        """Pinta os dias com disponibilidade no calendário."""
        cal.calevent_remove('all')
        ano, mes = cal.get_displayed_month()
        datas_disponiveis = database.listar_datas_disponiveis_por_mes(medico_id, ano, mes)
        for data_str in datas_disponiveis:
            try:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                cal.calevent_create(data_obj, 'Disponível', tags='disponivel')
            except ValueError:
                continue

    def atualizar_horarios_do_dia(event=None): # Adicionado event=None para ser usado como callback
        """Carrega e exibe os horários para o dia selecionado no calendário."""
        for i in tree_horarios.get_children(): tree_horarios.delete(i)
        data_selecionada = cal.get_date()
        lbl_data_selecionada.config(text=f"Horários para {data_selecionada}")
        data_db = formatar_data_para_db(data_selecionada)
        horarios = database.listar_disponibilidade_por_data(medico_id, data_db)
        for horario in horarios:
            tree_horarios.insert("", "end", values=(horario['id'], horario['hora_inicio'], horario['hora_fim']))

    def adicionar_horario():
        inicio, fim = entry_inicio.get().strip(), entry_fim.get().strip()
        data_selecionada_str = cal.get_date()
        data_db = formatar_data_para_db(data_selecionada_str)

        # Validações
        try:
            datetime.strptime(inicio, '%H:%M'); datetime.strptime(fim, '%H:%M')
        except ValueError:
            messagebox.showerror("Formato Inválido", "O formato do horário deve ser HH:MM.", parent=janela_disp); return
        if datetime.strptime(inicio, '%H:%M') >= datetime.strptime(fim, '%H:%M'):
            messagebox.showwarning("Lógica Inválida", "O horário de início deve ser anterior ao de fim.", parent=janela_disp); return

        try:
            database.adicionar_disponibilidade(medico_id, data_db, inicio, fim)
            entry_inicio.delete(0, 'end'); entry_fim.delete(0, 'end')
            atualizar_horarios_do_dia()
            marcar_dias_disponiveis() # Garante que o dia seja marcado
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível adicionar o horário: {e}", parent=janela_disp)

    def excluir_horario_selecionado():
        selected_item = tree_horarios.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Selecione um horário para excluir.", parent=janela_disp); return
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este horário?", parent=janela_disp):
            try:
                disponibilidade_id = tree_horarios.item(selected_item)['values'][0]
                database.excluir_disponibilidade(disponibilidade_id)
                atualizar_horarios_do_dia()
                marcar_dias_disponiveis() # Atualiza o calendário caso o dia fique sem horários
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Não foi possível excluir o horário: {e}", parent=janela_disp)

    # --- Botões e Eventos ---
    ttk.Button(add_frame, text="Adicionar", command=adicionar_horario).grid(row=0, column=4, padx=5)

    bottom_buttons_frame = ttk.Frame(right_frame)
    bottom_buttons_frame.pack(fill='x', side='bottom', pady=(10,0))
    ttk.Button(bottom_buttons_frame, text="Excluir Horário Selecionado", command=excluir_horario_selecionado).pack(side='left')
    ttk.Button(bottom_buttons_frame, text="Fechar", command=janela_disp.destroy).pack(side='right')

    # Bind de eventos do calendário
    cal.bind("<<CalendarSelected>>", atualizar_horarios_do_dia)
    cal.bind("<<CalendarMonthChanged>>", lambda e: marcar_dias_disponiveis())

    # Carregamento inicial
    marcar_dias_disponiveis()
    atualizar_horarios_do_dia()

def abrir_janela_agenda_geral(janela_pai):
    """Abre uma janela com a visão geral da disponibilidade de todos os médicos."""
    janela_agenda = tk.Toplevel(janela_pai)
    janela_agenda.title("Agenda Geral de Disponibilidade")
    janela_agenda.geometry("1000x600")
    janela_agenda.transient(janela_pai)
    janela_agenda.grab_set()

    main_frame = ttk.Frame(janela_agenda, padding=10)
    main_frame.pack(fill='both', expand=True)

    # --- Frame do Calendário (Topo) ---
    cal_frame = ttk.Frame(main_frame)
    cal_frame.pack(fill='x', pady=(0, 10))

    hoje = date.today()
    cal = Calendar(cal_frame, selectmode='day', year=hoje.year, month=hoje.month, day=hoje.day,
                   locale='pt_BR', date_pattern='dd/mm/y')
    cal.pack(side='left', padx=(0, 20))

    lbl_info = ttk.Label(cal_frame, text="Selecione uma data para ver a disponibilidade de todos os terapeutas.", font=("Helvetica", 11))
    lbl_info.pack(side='left', anchor='w')

    btn_atualizar_agenda = ttk.Button(cal_frame, text="Atualizar", command=lambda: atualizar_disponibilidade_geral())
    btn_atualizar_agenda.pack(side='right', padx=10)

    # --- Frame da Tabela de Disponibilidade (Abaixo) ---
    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill='both', expand=True)

    cols = ('terapeuta', 'horario_disponivel')
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
    tree.heading('terapeuta', text='Terapeuta')
    tree.column('terapeuta', width=300)
    tree.heading('horario_disponivel', text='Horário Disponível')
    tree.column('horario_disponivel', width=200, anchor='center')

    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)
    # The above code is original and does not use code from the referenced repository.

    def atualizar_disponibilidade_geral(event=None):
        """Busca e exibe a disponibilidade de todos os médicos para o dia selecionado."""
        for i in tree.get_children():
            tree.delete(i)

        data_selecionada = cal.get_date()
        data_db = formatar_data_para_db(data_selecionada)

        try:
            disponibilidades = database.listar_disponibilidade_geral_por_data(data_db)
            if not disponibilidades:
                tree.insert("", "end", values=("Nenhum terapeuta disponível nesta data.", ""))
            else:
                for disp in disponibilidades:
                    horario = f"{disp['hora_inicio']} - {disp['hora_fim']}"
                    tree.insert("", "end", values=(disp['medico_nome'], horario))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao buscar disponibilidade: {e}", parent=janela_agenda)

    # --- Binds e Carregamento Inicial ---
    cal.bind("<<CalendarSelected>>", atualizar_disponibilidade_geral)

    # Carrega a disponibilidade para o dia de hoje ao abrir
    atualizar_disponibilidade_geral()

def abrir_janela_relatorio_por_plano(janela_pai, data_inicio_db, data_fim_db):
    """Abre uma janela para exibir o relatório de receitas agrupadas por plano de saúde."""
    janela_relatorio = tk.Toplevel(janela_pai)
    janela_relatorio.title("Relatório de Receitas por Plano de Saúde")
    janela_relatorio.geometry("600x400")
    janela_relatorio.transient(janela_pai)
    janela_relatorio.grab_set()

    frame_relatorio = ttk.Frame(janela_relatorio, padding=10)
    frame_relatorio.pack(fill='both', expand=True)

    periodo_str = f"Período: {formatar_data_para_exibicao(data_inicio_db)} a {formatar_data_para_exibicao(data_fim_db)}"
    ttk.Label(frame_relatorio, text=periodo_str, font=("Helvetica", 11, "bold")).pack(pady=(0, 10))

    # Treeview para mostrar o relatório
    cols = ('plano', 'valor_total')
    tree_relatorio = ttk.Treeview(frame_relatorio, columns=cols, show='headings')
    tree_relatorio.heading('plano', text='Plano de Saúde')
    tree_relatorio.heading('valor_total', text='Valor Total Recebido (R$)')
    tree_relatorio.column('valor_total', anchor='e')
    tree_relatorio.pack(fill='both', expand=True)

    # Popula a tabela com os dados
    try:
        dados_agrupados = database.listar_receitas_agrupadas_por_plano(data_inicio_db, data_fim_db)
        total_geral = 0
        for item in dados_agrupados:
            plano = item['plano_nome']
            total = item['total_valor']
            total_geral += total
            tree_relatorio.insert("", "end", values=(plano, f"{total:.2f}"))
        
        # Adiciona uma linha com o total geral
        if dados_agrupados:
            tree_relatorio.insert("", "end", values=("", "")) # Linha separadora
            tree_relatorio.insert("", "end", values=("TOTAL GERAL", f"{total_geral:.2f}"), tags=('total_row',))
            tree_relatorio.tag_configure('total_row', font=('Helvetica', 10, 'bold'))

    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível gerar o relatório: {e}", parent=janela_relatorio)

def abrir_janela_pagamentos_pendentes(janela_pai, paciente_id, paciente_nome, callback_atualizar_lista):
    """Abre uma janela para gerenciar e quitar pagamentos pendentes de um paciente."""
    janela_pgto = tk.Toplevel(janela_pai)
    janela_pgto.title(f"Pagamentos Pendentes - {paciente_nome}")
    janela_pgto.geometry("500x400")
    janela_pgto.transient(janela_pai)
    janela_pgto.grab_set()

    frame = ttk.Frame(janela_pgto, padding=10)
    frame.pack(fill='both', expand=True)

    sessoes_pendentes = database.listar_sessoes_pendentes_por_paciente(paciente_id)

    if not sessoes_pendentes:
        ttk.Label(frame, text="Este paciente não possui pagamentos pendentes.", font=("Helvetica", 11)).pack(pady=20)
        ttk.Button(frame, text="Fechar", command=janela_pgto.destroy).pack(pady=10)
        return

    # Tabela de sessões pendentes
    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill='both', expand=True, pady=(0, 10))
    cols = ('data', 'valor')
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
    tree.heading('data', text='Data da Sessão'); tree.column('data', anchor='center', width=150)
    tree.heading('valor', text='Valor (R$)'); tree.column('valor', anchor='e', width=100)
    tree.pack(fill='both', expand=True)

    total_pendente = 0
    for sessao in sessoes_pendentes:
        valor = sessao.get('valor_sessao', 0.0)
        total_pendente += valor
        tree.insert("", "end", values=(formatar_data_para_exibicao(sessao['data_sessao']), f"{valor:.2f}"))

    # Frame de totais e botão de quitar
    bottom_frame = ttk.Frame(frame)
    bottom_frame.pack(fill='x')
    
    lbl_total = ttk.Label(bottom_frame, text=f"Total Pendente: R$ {total_pendente:.2f}", font=("Helvetica", 12, "bold"))
    lbl_total.pack(side='left', pady=5)

    def quitar_tudo():
        if messagebox.askyesno("Confirmar", f"Deseja marcar todas as {len(sessoes_pendentes)} sessões pendentes como 'Pagas'?", parent=janela_pgto):
            try:
                database.marcar_todas_sessoes_como_pagas(paciente_id)
                messagebox.showinfo("Sucesso", "Todos os pagamentos pendentes foram quitados.", parent=janela_pgto)
                janela_pgto.destroy()
                callback_atualizar_lista() # Atualiza a lista de pacientes
            except sqlite3.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Não foi possível atualizar os pagamentos: {e}", parent=janela_pgto)

    ttk.Button(bottom_frame, text="Marcar Todas como Pagas", command=quitar_tudo).pack(side='right', pady=5)

def abrir_janela_controle_pagamentos(janela_pai):
    """Abre uma janela centralizada para gerenciar todos os pagamentos pendentes."""
    janela_ctrl_pgto = tk.Toplevel(janela_pai)
    janela_ctrl_pgto.title("Controle de Pagamentos Pendentes")
    janela_ctrl_pgto.geometry("700x500")
    janela_ctrl_pgto.transient(janela_pai)
    janela_ctrl_pgto.grab_set()

    frame = ttk.Frame(janela_ctrl_pgto, padding=10)
    frame.pack(fill='both', expand=True)

    # --- Frame de Busca ---
    busca_frame = ttk.Frame(frame)
    busca_frame.pack(fill='x', pady=(0, 10))
    ttk.Label(busca_frame, text="Buscar por Paciente:").pack(side='left', padx=(0, 5))
    entry_busca = ttk.Entry(busca_frame, width=40)
    entry_busca.pack(side='left', expand=True, fill='x')
    
    # --- Tabela de Sessões Pendentes ---
    tree_frame = ttk.Frame(frame)
    tree_frame.pack(fill='both', expand=True)
    cols = ('ID', 'Paciente', 'Data da Sessão', 'Valor')
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='extended')
    tree.heading('ID', text='ID'); tree.column('ID', width=0, stretch=tk.NO) # Oculto
    tree.heading('Paciente', text='Paciente'); tree.column('Paciente', width=300)
    tree.heading('Data da Sessão', text='Data da Sessão'); tree.column('Data da Sessão', width=150, anchor='center')
    tree.heading('Valor', text='Valor (R$)'); tree.column('Valor', width=100, anchor='e')
    tree.pack(side='left', fill='both', expand=True)
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side='right', fill='y')

    def recarregar_lista_pendencias():
        termo_busca = entry_busca.get().strip()
        for i in tree.get_children(): tree.delete(i)
        try:
            sessoes_pendentes = database.listar_todas_sessoes_pendentes(termo_busca)
            for sessao in sessoes_pendentes:
                valor = sessao.get('valor_sessao', 0.0)
                tree.insert("", "end", iid=sessao['id'], values=(
                    sessao['id'], sessao['paciente_nome'], 
                    formatar_data_para_exibicao(sessao['data_sessao']), 
                    f"{valor:.2f}"
                ))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao carregar pendências: {e}", parent=janela_ctrl_pgto)

    def marcar_selecionadas_como_pagas():
        itens_selecionados = tree.selection()
        if not itens_selecionados:
            messagebox.showwarning("Nenhuma Seleção", "Selecione uma ou mais sessões para marcar como pagas.", parent=janela_ctrl_pgto)
            return
        
        if messagebox.askyesno("Confirmar Pagamento", f"Deseja marcar as {len(itens_selecionados)} sessões selecionadas como 'Pagas'?", parent=janela_ctrl_pgto):
            try:
                for item_id in itens_selecionados:
                    valores = tree.item(item_id, 'values')
                    valor_sessao = float(valores[3])
                    database.atualizar_financeiro_sessao(item_id, valor_sessao, 'Pago')
                messagebox.showinfo("Sucesso", "Pagamentos registrados com sucesso!", parent=janela_ctrl_pgto)
                recarregar_lista_pendencias()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível atualizar os pagamentos: {e}", parent=janela_ctrl_pgto)

    ttk.Button(busca_frame, text="Buscar", command=recarregar_lista_pendencias).pack(side='left', padx=5)
    ttk.Button(frame, text="Marcar Selecionadas como Pagas", command=marcar_selecionadas_como_pagas).pack(side='bottom', pady=(10, 0))
    recarregar_lista_pendencias()

class FluxoCaixaWindow(tk.Toplevel):
    """Janela de gestão financeira (Fluxo de Caixa)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gestão Financeira - Fluxo de Caixa")
        self.geometry("950x650")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self.carregar_dados_financeiros()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        # --- Frame de Filtro de Período ---
        filtro_frame = ttk.Frame(main_frame)
        filtro_frame.pack(fill='x', pady=(0, 10))
        
        hoje = date.today()
        primeiro_dia_mes = hoje.replace(day=1)

        ttk.Label(filtro_frame, text="De:").pack(side='left', padx=(0, 5))
        self.cal_inicio = Calendar(filtro_frame, selectmode='day', date_pattern='dd/mm/y', year=primeiro_dia_mes.year, month=primeiro_dia_mes.month, day=primeiro_dia_mes.day)
        self.cal_inicio.pack(side='left')

        ttk.Label(filtro_frame, text="Até:").pack(side='left', padx=(20, 5))
        self.cal_fim = Calendar(filtro_frame, selectmode='day', date_pattern='dd/mm/y')
        self.cal_fim.pack(side='left')

        btn_filtrar = ttk.Button(filtro_frame, text="Filtrar Período", command=self.carregar_dados_financeiros)
        btn_filtrar.pack(side='left', padx=20, anchor='s')

        # --- Notebook com Abas ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=10)

        # --- Aba de Movimentações de Sessões ---
        aba_receitas = ttk.Frame(notebook, padding=10)
        notebook.add(aba_receitas, text=' Movimentações de Sessões ')
        cols_receitas = ('id', 'data', 'paciente', 'terapeuta', 'valor', 'status')
        self.tree_receitas = ttk.Treeview(aba_receitas, columns=cols_receitas, show='headings')
        self.tree_receitas.heading('id', text='ID'); self.tree_receitas.column('id', width=0, stretch=tk.NO)
        self.tree_receitas.heading('data', text='Data'); self.tree_receitas.column('data', width=100, anchor='center')
        self.tree_receitas.heading('paciente', text='Paciente'); self.tree_receitas.column('paciente', width=250)
        self.tree_receitas.heading('terapeuta', text='Terapeuta'); self.tree_receitas.column('terapeuta', width=250)
        self.tree_receitas.heading('valor', text='Valor (R$)'); self.tree_receitas.column('valor', width=100, anchor='e')
        self.tree_receitas.heading('status', text='Status'); self.tree_receitas.column('status', width=100, anchor='center')
        self.tree_receitas.pack(fill='both', expand=True)
        self.tree_receitas.tag_configure('pago', background='#d9ead3')
        self.tree_receitas.tag_configure('pendente', background='#fce5cd')

        # --- Aba de Despesas ---
        aba_despesas = ttk.Frame(notebook, padding=10)
        notebook.add(aba_despesas, text=' Despesas ')
        cols_despesas = ('data', 'descricao', 'valor')
        self.tree_despesas = ttk.Treeview(aba_despesas, columns=cols_despesas, show='headings')
        self.tree_despesas.heading('data', text='Data'); self.tree_despesas.column('data', width=100, anchor='center')
        self.tree_despesas.heading('descricao', text='Descrição'); self.tree_despesas.column('descricao', width=400)
        self.tree_despesas.heading('valor', text='Valor (R$)'); self.tree_despesas.column('valor', width=100, anchor='e')
        self.tree_despesas.pack(fill='both', expand=True)

        # --- Frame de Adicionar Despesa ---
        add_despesa_frame = ttk.LabelFrame(aba_despesas, text="Adicionar Nova Despesa", padding=10)
        add_despesa_frame.pack(fill='x', pady=(10, 0))
        ttk.Label(add_despesa_frame, text="Descrição:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_desc_despesa = ttk.Entry(add_despesa_frame, width=40)
        self.entry_desc_despesa.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(add_despesa_frame, text="Valor:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_valor_despesa = ttk.Entry(add_despesa_frame, width=15)
        self.entry_valor_despesa.grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(add_despesa_frame, text="Data:").grid(row=0, column=4, padx=5, pady=5)
        self.entry_data_despesa = ttk.Entry(add_despesa_frame, width=15)
        self.entry_data_despesa.insert(0, hoje.strftime('%d/%m/%Y'))
        self.entry_data_despesa.grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(add_despesa_frame, text="Adicionar", command=self.adicionar_nova_despesa).grid(row=0, column=6, padx=5)

        # --- Frame de Totais e Saldo ---
        saldo_frame = ttk.Frame(main_frame)
        saldo_frame.pack(fill='x', pady=5)
        self.lbl_total_recebido = ttk.Label(saldo_frame, text="Total Recebido: R$ 0.00", font=("Helvetica", 11, "bold"), foreground="blue")
        self.lbl_total_recebido.pack(side='left', padx=10)
        self.lbl_total_a_receber = ttk.Label(saldo_frame, text="Total a Receber: R$ 0.00", font=("Helvetica", 11, "bold"), foreground="orange")
        self.lbl_total_a_receber.pack(side='left', padx=10)
        self.lbl_total_despesas = ttk.Label(saldo_frame, text="Total Despesas: R$ 0.00", font=("Helvetica", 11, "bold"), foreground="red")
        self.lbl_total_despesas.pack(side='left', padx=10)
        self.lbl_saldo = ttk.Label(saldo_frame, text="Saldo: R$ 0.00", font=("Helvetica", 12, "bold"), foreground="green")
        self.lbl_saldo.pack(side='right', padx=10)

        # --- Frame de Botões de Ação ---
        botoes_financeiro_frame = ttk.Frame(main_frame)
        botoes_financeiro_frame.pack(fill='x', pady=(5,0))
        btn_relatorio = ttk.Button(botoes_financeiro_frame, text="Gerar Relatório por Plano de Saúde", command=self.gerar_relatorio_planos)
        btn_relatorio.pack(side='left')

        # --- Menu de Contexto para a tabela de receitas ---
        self.menu_contexto_receitas = tk.Menu(self.tree_receitas, tearoff=0)
        self.menu_contexto_receitas.add_command(label="Marcar como Pago", command=lambda: self.alterar_status_pagamento_sessao('Pago'))
        self.menu_contexto_receitas.add_command(label="Marcar como Pendente", command=lambda: self.alterar_status_pagamento_sessao('Pendente'))
        self.tree_receitas.bind("<Button-3>", self.mostrar_menu_receitas)

    def carregar_dados_financeiros(self):
        data_inicio_db = formatar_data_para_db(self.cal_inicio.get_date())
        data_fim_db = formatar_data_para_db(self.cal_fim.get_date())

        for i in self.tree_receitas.get_children(): self.tree_receitas.delete(i)
        for i in self.tree_despesas.get_children(): self.tree_despesas.delete(i)

        total_recebido, total_a_receber, total_despesas = 0, 0, 0

        sessoes = database.listar_sessoes_financeiro_por_periodo(data_inicio_db, data_fim_db)
        for s in sessoes:
            valor = s.get('valor_sessao', 0.0)
            status = s.get('status_pagamento', 'Pendente')
            tag = 'pago' if status == 'Pago' else 'pendente'
            if status == 'Pago':
                total_recebido += valor
            else:
                total_a_receber += valor
            
            self.tree_receitas.insert("", "end", iid=s['id'], values=(
                s['id'], formatar_data_para_exibicao(s['data_sessao']), s['paciente_nome'], 
                s['medico_nome'], f"{valor:.2f}", status
            ), tags=(tag,))

        despesas = database.listar_despesas_por_periodo(data_inicio_db, data_fim_db)
        for d in despesas:
            valor = d.get('valor', 0.0)
            total_despesas += valor
            self.tree_despesas.insert("", "end", values=(formatar_data_para_exibicao(d['data']), d['descricao'], f"{valor:.2f}"))

        saldo = total_recebido - total_despesas
        self.lbl_total_recebido.config(text=f"Total Recebido: R$ {total_recebido:.2f}")
        self.lbl_total_a_receber.config(text=f"Total a Receber: R$ {total_a_receber:.2f}")
        self.lbl_total_despesas.config(text=f"Total Despesas: R$ {total_despesas:.2f}")
        self.lbl_saldo.config(text=f"Saldo: R$ {saldo:.2f}")

    def adicionar_nova_despesa(self):
        """Adiciona uma nova despesa a partir dos campos de entrada."""
        desc = self.entry_desc_despesa.get().strip()
        valor_str = self.entry_valor_despesa.get().replace(',', '.').strip()
        data_str = self.entry_data_despesa.get().strip()

        if not (desc and valor_str and data_str):
            messagebox.showerror("Erro", "Todos os campos da despesa são obrigatórios.", parent=self)
            return

        data_db = formatar_data_para_db(data_str)
        if not data_db:
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/AAAA.", parent=self)
            return
        
        try:
            valor = float(valor_str)
            database.adicionar_despesa(desc, valor, data_db)
            self.entry_desc_despesa.delete(0, 'end')
            self.entry_valor_despesa.delete(0, 'end')
            self.carregar_dados_financeiros()
        except ValueError:
            messagebox.showerror("Erro", "O valor da despesa deve ser um número.", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível salvar a despesa: {e}", parent=self)

    def gerar_relatorio_planos(self):
        """Abre a janela de relatório de receitas por plano de saúde."""
        data_inicio_db = formatar_data_para_db(self.cal_inicio.get_date())
        data_fim_db = formatar_data_para_db(self.cal_fim.get_date())
        abrir_janela_relatorio_por_plano(self, data_inicio_db, data_fim_db)

    def mostrar_menu_receitas(self, event):
        """Exibe o menu de contexto na tabela de receitas."""
        item_id = self.tree_receitas.identify_row(event.y)
        if item_id:
            self.tree_receitas.selection_set(item_id)
            self.tree_receitas.focus(item_id)
            self.menu_contexto_receitas.post(event.x_root, event.y_root)

    def alterar_status_pagamento_sessao(self, novo_status):
        """Altera o status de pagamento da sessão selecionada na tabela de receitas."""
        selected_item_id = self.tree_receitas.focus()
        if not selected_item_id:
            return
        
        try:
            valores = self.tree_receitas.item(selected_item_id, 'values')
            valor_atual = float(valores[4]) # O valor está na 5ª coluna (índice 4)
            database.atualizar_financeiro_sessao(selected_item_id, valor_atual, novo_status)
            self.carregar_dados_financeiros()
        except (ValueError, IndexError) as e:
            messagebox.showerror("Erro", f"Não foi possível obter os dados da sessão: {e}", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível atualizar o status: {e}", parent=self)

# --- Funções para Abrir Janelas de Pacientes ---

def abrir_janela_cadastro(janela_pai, callback_atualizar=None):
    """Abre uma nova janela para o cadastro de pacientes."""
    janela_cadastro = tk.Toplevel(janela_pai)
    janela_cadastro.title("Cadastrar Novo Paciente")
    janela_cadastro.geometry("600x650")
    janela_cadastro.resizable(True, True)
    janela_cadastro.transient(janela_pai)
    janela_cadastro.grab_set()

    frame = tk.Frame(janela_cadastro, padx=20, pady=20)
    frame.pack(expand=True, fill='both')
    frame.columnconfigure(1, weight=1)

    # --- Campos de Dados Pessoais ---
    tk.Label(frame, text="Nome Completo:").grid(row=0, column=0, sticky="w", pady=2)
    entry_nome = tk.Entry(frame)
    entry_nome.grid(row=0, column=1, pady=2, sticky="ew")
    entry_nome.focus_set() # Foco automático no primeiro campo

    tk.Label(frame, text="Data de Nascimento (DD/MM/AAAA):").grid(row=1, column=0, sticky="w", pady=2)
    entry_data = tk.Entry(frame)
    entry_data.grid(row=1, column=1, pady=2, sticky="ew")

    tk.Label(frame, text="Nome do Responsável:").grid(row=2, column=0, sticky="w", pady=2)
    entry_resp = tk.Entry(frame)
    entry_resp.grid(row=2, column=1, pady=2, sticky="ew")

    tk.Label(frame, text="Telefone do Responsável:").grid(row=3, column=0, sticky="w", pady=2)
    entry_tel_resp = tk.Entry(frame)
    entry_tel_resp.grid(row=3, column=1, pady=2, sticky="ew")

    tk.Label(frame, text="Plano de Saúde:").grid(row=4, column=0, sticky="w", pady=2)
    planos = database.listar_planos_saude()
    planos_map = {p['nome']: p['id'] for p in planos}
    combo_plano = ttk.Combobox(frame, values=list(planos_map.keys()), state='readonly')
    if planos:
        combo_plano.set(planos[0]['nome']) # Define 'Particular' como padrão
    combo_plano.grid(row=4, column=1, pady=2, sticky="ew")

    tk.Label(frame, text="Valor Padrão Sessão (R$):").grid(row=5, column=0, sticky="w", pady=2)
    entry_valor = tk.Entry(frame)
    entry_valor.grid(row=5, column=1, pady=2, sticky="ew")
    entry_valor.insert(0, "0.00")

    # --- Seção de Terapias Automáticas ---
    terapias_frame = ttk.LabelFrame(frame, text="Plano Terapêutico Inicial", padding=10)
    terapias_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(15, 5))
    terapias_frame.columnconfigure(1, weight=1)

    tk.Label(terapias_frame, text="Nível de Autismo:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    combo_nivel = ttk.Combobox(terapias_frame, values=list(TERAPIAS_POR_NIVEL.keys()), state='readonly')
    combo_nivel.grid(row=0, column=1, sticky="ew")

    text_terapias = tk.Text(terapias_frame, height=15, wrap='word')
    text_terapias.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
    terapias_frame.rowconfigure(1, weight=1)

    def atualizar_terapias(event):
        nivel_selecionado = combo_nivel.get()
        texto_sugerido = TERAPIAS_POR_NIVEL.get(nivel_selecionado, "")
        text_terapias.delete("1.0", "end")
        text_terapias.insert("1.0", texto_sugerido)

    combo_nivel.bind("<<ComboboxSelected>>", atualizar_terapias)

    btn_salvar = tk.Button(
        frame,
        text="Salvar Cadastro",
        command=lambda: salvar_paciente(janela_cadastro, entry_nome, entry_data, entry_resp, entry_tel_resp, combo_plano, planos_map, entry_valor, text_terapias)
    )
    btn_salvar.grid(row=7, column=1, sticky="e", pady=15)

    # Espera a janela de cadastro ser fechada e depois chama o callback para atualizar a lista.
    janela_pai.wait_window(janela_cadastro)
    if callback_atualizar:
        callback_atualizar()

def abrir_janela_edicao(janela_pai, paciente_id, callback_atualizar):
    """Abre uma janela para editar os dados de um paciente."""
    paciente_data = database.buscar_paciente_por_id(paciente_id)
    if not paciente_data:
        messagebox.showerror("Erro", "Paciente não encontrado.", parent=janela_pai)
        return

    janela_edicao = tk.Toplevel(janela_pai)
    janela_edicao.title(f"Editar Paciente - {paciente_data['nome_completo']}")
    janela_edicao.geometry("600x650")
    janela_edicao.resizable(True, True)
    janela_edicao.transient(janela_pai)
    janela_edicao.grab_set()

    frame = tk.Frame(janela_edicao, padx=20, pady=20)
    frame.pack(expand=True, fill='both')
    frame.columnconfigure(1, weight=1)

    # --- Campos de Dados Pessoais ---
    tk.Label(frame, text="Nome Completo:").grid(row=0, column=0, sticky="w", pady=2)
    entry_nome = tk.Entry(frame)
    entry_nome.grid(row=0, column=1, pady=2, sticky="ew")
    entry_nome.insert(0, paciente_data['nome_completo'])
    entry_nome.focus_set()

    tk.Label(frame, text="Data de Nascimento (DD/MM/AAAA):").grid(row=1, column=0, sticky="w", pady=2)
    entry_data = tk.Entry(frame)
    entry_data.grid(row=1, column=1, pady=2, sticky="ew")
    entry_data.insert(0, formatar_data_para_exibicao(paciente_data['data_nascimento']))

    tk.Label(frame, text="Nome do Responsável:").grid(row=2, column=0, sticky="w", pady=2)
    entry_resp = tk.Entry(frame)
    entry_resp.grid(row=2, column=1, pady=2, sticky="ew")
    entry_resp.insert(0, paciente_data['nome_responsavel'])

    tk.Label(frame, text="Telefone do Responsável:").grid(row=3, column=0, sticky="w", pady=2)
    entry_tel_resp = tk.Entry(frame)
    entry_tel_resp.grid(row=3, column=1, pady=2, sticky="ew")
    entry_tel_resp.insert(0, paciente_data.get('telefone_responsavel') or "")

    tk.Label(frame, text="Plano de Saúde:").grid(row=4, column=0, sticky="w", pady=2)
    planos = database.listar_planos_saude()
    planos_map = {p['nome']: p['id'] for p in planos}
    inv_planos_map = {v: k for k, v in planos_map.items()}
    combo_plano = ttk.Combobox(frame, values=list(planos_map.keys()), state='readonly')
    plano_atual_id = paciente_data.get('plano_saude_id')
    if plano_atual_id and plano_atual_id in inv_planos_map:
        combo_plano.set(inv_planos_map[plano_atual_id])
    elif planos:
        combo_plano.set(planos[0]['nome'])
    combo_plano.grid(row=4, column=1, pady=2, sticky="ew")

    tk.Label(frame, text="Valor Padrão Sessão (R$):").grid(row=5, column=0, sticky="w", pady=2)
    entry_valor = tk.Entry(frame)
    entry_valor.grid(row=5, column=1, pady=2, sticky="ew")
    entry_valor.insert(0, f"{paciente_data.get('valor_sessao_padrao', 0.0):.2f}")

    # --- Seção de Terapias (agora na edição também) ---
    terapias_frame = ttk.LabelFrame(frame, text="Plano Terapêutico / Anamnese", padding=10)
    terapias_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(15, 5))
    terapias_frame.columnconfigure(1, weight=1)

    tk.Label(terapias_frame, text="Nível de Autismo (sobrescreve o texto abaixo):").grid(row=0, column=0, sticky="w", padx=(0, 5))
    combo_nivel = ttk.Combobox(terapias_frame, values=list(TERAPIAS_POR_NIVEL.keys()), state='readonly')
    combo_nivel.grid(row=0, column=1, sticky="ew")

    text_terapias = tk.Text(terapias_frame, height=15, wrap='word')
    text_terapias.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
    terapias_frame.rowconfigure(1, weight=1)

    # Carrega a anamnese existente do prontuário
    prontuario = database.buscar_ou_criar_prontuario(paciente_id)
    text_terapias.insert("1.0", prontuario.get('anamnese', ''))

    def atualizar_terapias(event):
        nivel_selecionado = combo_nivel.get()
        texto_sugerido = TERAPIAS_POR_NIVEL.get(nivel_selecionado, "")
        text_terapias.delete("1.0", "end")
        text_terapias.insert("1.0", texto_sugerido)

    combo_nivel.bind("<<ComboboxSelected>>", atualizar_terapias)

    btn_salvar = tk.Button(
        frame,
        text="Salvar Alterações",
        command=lambda: salvar_alteracoes_paciente(janela_edicao, entry_nome, entry_data, entry_resp, entry_tel_resp, combo_plano, planos_map, entry_valor, text_terapias, paciente_id)
    )
    btn_salvar.grid(row=7, column=1, sticky="e", pady=15)

    # Espera a janela de edição ser fechada e depois chama o callback para atualizar a lista.
    janela_pai.wait_window(janela_edicao)
    if callback_atualizar:
        callback_atualizar()

def criar_abas_sessao(frame_pai):
    """Cria e retorna um notebook com abas para o formulário de sessão."""
    notebook = ttk.Notebook(frame_pai)
    notebook.pack(expand=True, fill='both', pady=5)

    # Aba 1: Avaliação da Sessão
    aba1 = ttk.Frame(notebook, padding=10)
    notebook.add(aba1, text=' Avaliação da Sessão ')

    # Aba 2: Plano Terapêutico
    aba2 = ttk.Frame(notebook, padding=10)
    notebook.add(aba2, text=' Plano Terapêutico ')

    # --- Widgets da Aba 1 ---
    frame_evolucao = ttk.Frame(aba1)
    frame_evolucao.pack(fill='x', pady=(0, 10))
    ttk.Label(frame_evolucao, text="Nível de Evolução:").pack(side='left')
    combo_evolucao = ttk.Combobox(frame_evolucao, values=["Iniciante", "Intermediário", "Avançado", "Manutenção"])
    combo_evolucao.pack(side='left', padx=5)

    ttk.Label(aba1, text="Resumo da Sessão (o que foi trabalhado):").pack(anchor='w', pady=(5,0))
    text_resumo = tk.Text(aba1, width=50, height=8, wrap='word')
    text_resumo.pack(expand=True, fill='both', pady=(0, 10))

    ttk.Label(aba1, text="Observações sobre a Evolução do Paciente:").pack(anchor='w')
    text_obs_evolucao = tk.Text(aba1, width=50, height=8, wrap='word')
    text_obs_evolucao.pack(expand=True, fill='both')

    # --- Widgets da Aba 2 ---
    ttk.Label(aba2, text="Plano Terapêutico (atividades, metas e estratégias para as próximas sessões):").pack(anchor='w')
    text_plano = tk.Text(aba2, width=50, height=15, wrap='word')
    text_plano.pack(expand=True, fill='both', pady=5)

    return {
        "resumo": text_resumo, "evolucao": combo_evolucao, 
        "obs_evolucao": text_obs_evolucao, "plano": text_plano
    }

def abrir_janela_detalhes_sessao(janela_pai, sessao_id):
    """Abre uma janela para exibir os detalhes completos de uma sessão."""
    sessao_data = database.buscar_sessao_por_id(sessao_id)
    if not sessao_data:
        messagebox.showerror("Erro", "Sessão não encontrada.", parent=janela_pai)
        return
    
    janela_detalhes = tk.Toplevel(janela_pai)
    data_exibicao = formatar_data_para_exibicao(sessao_data['data_sessao'])
    janela_detalhes.title(f"Detalhes da Sessão - {data_exibicao if data_exibicao else 'Data Inválida'}")
    janela_detalhes.geometry("600x500")
    janela_detalhes.resizable(True, True)
    janela_detalhes.transient(janela_pai)
    janela_detalhes.grab_set()

    frame = ttk.Frame(janela_detalhes, padding="15")
    frame.pack(expand=True, fill='both')
    
    widgets = criar_abas_sessao(frame)
    
    # Preenche os dados e desabilita a edição
    widgets['resumo'].insert('1.0', sessao_data['resumo_sessao'] or "")
    widgets['evolucao'].set(sessao_data['nivel_evolucao'] or "")
    widgets['obs_evolucao'].insert('1.0', sessao_data['observacoes_evolucao'] or "")
    widgets['plano'].insert('1.0', sessao_data['plano_terapeutico'] or "")

    for w in widgets.values():
        if isinstance(w, (tk.Text, ttk.Entry, ttk.Combobox)):
            w.config(state='disabled')

    ttk.Button(frame, text="Fechar", command=janela_detalhes.destroy).pack(side='bottom', pady=(10, 0))

def abrir_janela_sessoes(janela_pai, paciente_id, paciente_nome, callback_atualizar_calendario):
    """Abre uma janela para listar e gerenciar as sessões de um paciente."""
    janela_sessoes = tk.Toplevel(janela_pai)
    janela_sessoes.title(f"Sessões de {paciente_nome}")
    janela_sessoes.geometry("800x500")
    janela_sessoes.transient(janela_pai)
    janela_sessoes.grab_set()
    # Garante que o calendário seja atualizado se a janela for fechada
    janela_sessoes.bind("<Destroy>", lambda e: callback_atualizar_calendario() if e.widget == janela_sessoes else None)

    frame = ttk.Frame(janela_sessoes, padding="10")
    frame.pack(expand=True, fill='both')

    # Tabela de Sessões
    tree_frame = ttk.Frame(frame)
    tree_frame.pack(expand=True, fill='both')
    cols = ('ID', 'Data', 'Horário', 'Terapeuta', 'Valor', 'Status')
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
    
    tree.heading('ID', text='ID')
    tree.column('ID', width=50, anchor='center')
    tree.heading('Data', text='Data')
    tree.column('Data', width=100, anchor='center')
    tree.heading('Horário', text='Horário')
    tree.column('Horário', width=80, anchor='center')
    tree.heading('Terapeuta', text='Terapeuta')
    tree.column('Terapeuta', width=250)
    tree.heading('Valor', text='Valor (R$)')
    tree.column('Valor', width=100, anchor='e')
    tree.heading('Status', text='Status Pagamento')
    tree.column('Status', width=120, anchor='center')
    
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Adicionando tags para colorir as linhas
    tree.tag_configure('pago', background='#d9ead3') # Verde claro
    tree.tag_configure('pendente', background='#fce5cd') # Laranja claro

    def recarregar_sessoes():
        for i in tree.get_children():
            tree.delete(i)
        try:
            for sessao in database.listar_sessoes_por_paciente(paciente_id):
                data_exibicao = formatar_data_para_exibicao(sessao['data_sessao'])
                valor = sessao.get('valor_sessao', 0.0)
                status = sessao.get('status_pagamento', 'Pendente')

                tag = ''
                if status == 'Pago':
                    tag = 'pago'
                elif status == 'Pendente':
                    tag = 'pendente'

                tree.insert("", "end", iid=sessao['id'], values=(
                    sessao['id'], data_exibicao, sessao['hora_inicio_sessao'] or '',
                    sessao['medico_nome'] or 'Não definido',
                    f"{valor:.2f}", status
                ), tags=(tag,))
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar sessões: {e}", parent=janela_sessoes)

    def callback_combinado():
        """Função que atualiza tanto a lista de sessões quanto o calendário principal."""
        recarregar_sessoes()
        if callback_atualizar_calendario:
            callback_atualizar_calendario()

    # --- Lógica do Menu de Contexto (Botão Direito) ---
    def marcar_status_pagamento(novo_status):
        """Atualiza o status de pagamento da sessão selecionada."""
        selected_item_id = tree.focus()
        if not selected_item_id:
            return
        
        try:
            # Pega o valor atual para não o zerar acidentalmente
            valores = tree.item(selected_item_id, 'values')
            valor_atual = float(valores[4])
            
            database.atualizar_financeiro_sessao(selected_item_id, valor_atual, novo_status)
            recarregar_sessoes() # Atualiza a lista para refletir a mudança
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível atualizar o status: {e}", parent=janela_sessoes)

    def mostrar_menu_contexto(event):
        """Exibe o menu de contexto ao clicar com o botão direito."""
        item_id = tree.identify_row(event.y)
        if item_id:
            tree.selection_set(item_id)
            tree.focus(item_id)
            menu_contexto.post(event.x_root, event.y_root)

    def ao_clicar_duas_vezes(event):
        """Abre os detalhes da sessão ao dar um duplo clique."""
        item_id = tree.focus()
        if not item_id:
            return
        abrir_janela_detalhes_sessao(janela_sessoes, item_id)

    # --- Configuração dos Menus e Eventos ---
    menu_contexto = tk.Menu(tree, tearoff=0)
    menu_contexto.add_command(label="Marcar como Pago", command=lambda: marcar_status_pagamento('Pago'))
    menu_contexto.add_command(label="Marcar como Pendente", command=lambda: marcar_status_pagamento('Pendente'))
    menu_contexto.add_separator()
    menu_contexto.add_command(label="Ver Detalhes da Sessão", command=lambda: abrir_detalhes_selecionado())
    menu_contexto.add_command(label="Gerar Relatório PDF", command=lambda: gerar_relatorio_selecionado())

    tree.bind("<Button-3>", mostrar_menu_contexto) # Botão direito do mouse
    tree.bind("<Double-1>", ao_clicar_duas_vezes)

    # Botões de Ação
    botoes_frame = ttk.Frame(frame, padding=(0, 10, 0, 0))
    botoes_frame.pack(fill='x', side='bottom')
    
    btn_adicionar = ttk.Button(
        botoes_frame, 
        text="Adicionar Nova Sessão", 
        command=lambda: abrir_janela_form_sessao(janela_sessoes, callback_combinado, paciente_id=paciente_id)
    )
    btn_adicionar.pack(side='left', padx=5)

    btn_editar = ttk.Button(
        botoes_frame,
        text="Editar Sessão",
        command=lambda: editar_sessao_selecionada()
    )
    btn_editar.pack(side='left', padx=5)

    ttk.Button(botoes_frame, text="Ver Detalhes", command=abrir_detalhes_selecionado).pack(side='left', padx=5)

    def editar_sessao_selecionada():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma sessão para editar.", parent=janela_sessoes)
            return
        sessao_id = tree.item(selected_item)['values'][0]
        abrir_janela_edicao_sessao(janela_sessoes, sessao_id, callback_combinado)

    def abrir_detalhes_selecionado():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma sessão para ver os detalhes.", parent=janela_sessoes)
            return
        abrir_janela_detalhes_sessao(janela_sessoes, selected_item)

    def gerar_relatorio_selecionado():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma sessão para gerar o relatório.", parent=janela_sessoes)
            return
        gerar_relatorio_sessao_pdf(janela_sessoes, selected_item)

    def excluir_sessao_selecionada():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma sessão para excluir.", parent=janela_sessoes)
            return
        
        sessao_id = tree.item(selected_item)['values'][0]
        confirmar = messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja excluir esta sessão?", parent=janela_sessoes)
        if confirmar:
            try:
                database.excluir_sessao(sessao_id)
                messagebox.showinfo("Sucesso", "Sessão excluída com sucesso.", parent=janela_sessoes)
                callback_combinado() # Atualiza lista e calendário
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao excluir sessão: {e}", parent=janela_sessoes)

    ttk.Button(botoes_frame, text="Gerar Relatório PDF", command=gerar_relatorio_selecionado).pack(side='right', padx=5)
    ttk.Button(botoes_frame, text="Excluir Sessão", command=excluir_sessao_selecionada).pack(side='right', padx=5)

    # Carrega os dados iniciais
    recarregar_sessoes()

def abrir_janela_form_sessao(janela_pai, callback_atualizar, paciente_id=None, sessao_id=None):
    """Abre um formulário para adicionar ou editar uma sessão."""
    janela_form = tk.Toplevel(janela_pai)
    janela_form.title("Registrar Nova Sessão" if not sessao_id else "Editar Sessão")
    janela_form.geometry("600x550")
    janela_form.resizable(True, True)
    janela_form.transient(janela_pai)
    janela_form.grab_set()

    frame = ttk.Frame(janela_form, padding="15")
    frame.pack(expand=True, fill='both')

    # --- Frame para dados da sessão (topo) ---
    top_form_frame = ttk.Frame(frame)
    top_form_frame.pack(fill='x', pady=(0, 15))
    top_form_frame.columnconfigure(1, weight=1)
    top_form_frame.columnconfigure(3, weight=1)

    # Data
    ttk.Label(top_form_frame, text="Data:").grid(row=0, column=0, sticky='w', padx=(0, 5), pady=2)
    entry_data = ttk.Entry(top_form_frame)
    entry_data.grid(row=0, column=1, sticky='ew', pady=2)
    entry_data.focus_set()

    # Horários
    ttk.Label(top_form_frame, text="Início:").grid(row=0, column=2, sticky='w', padx=(10, 5), pady=2)
    entry_inicio = ttk.Entry(top_form_frame)
    entry_inicio.grid(row=0, column=3, sticky='ew', pady=2)

    ttk.Label(top_form_frame, text="Fim:").grid(row=1, column=2, sticky='w', padx=(10, 5), pady=2)
    entry_fim = ttk.Entry(top_form_frame)
    entry_fim.grid(row=1, column=3, sticky='ew', pady=2)

    # Médico/Terapeuta
    ttk.Label(top_form_frame, text="Terapeuta:").grid(row=1, column=0, sticky='w', padx=(0, 5), pady=2)
    medicos = database.listar_medicos()
    medico_map = {m['nome_completo']: m['id'] for m in medicos}
    combo_medico = ttk.Combobox(top_form_frame, values=list(medico_map.keys()), state='readonly')
    combo_medico.grid(row=1, column=1, sticky='ew', pady=2)

    # --- Abas e Dicionário de Widgets ---
    # Cria as abas e obtém o dicionário de widgets delas
    widgets = criar_abas_sessao(frame)
    
    # Adiciona os widgets do topo ao dicionário para serem acessados pelas funções de salvar
    widgets['data'] = entry_data
    widgets['horario'] = entry_inicio
    widgets['hora_fim'] = entry_fim
    widgets['combo_medico'] = combo_medico
    widgets['medico_map'] = medico_map

    # --- Preenchimento dos dados (Modo Edição vs. Criação) ---
    if sessao_id:  # Modo de edição
        sessao_data = database.buscar_sessao_por_id(sessao_id)
        if not sessao_data:
            messagebox.showerror("Erro", "Sessão não encontrada.", parent=janela_form)
            janela_form.destroy()
            return

        # Preenche os campos do topo
        entry_data.insert(0, formatar_data_para_exibicao(sessao_data['data_sessao']))
        entry_inicio.insert(0, sessao_data.get('hora_inicio_sessao') or "")
        entry_fim.insert(0, sessao_data.get('hora_fim_sessao') or "")
        
        # Seleciona o médico no combobox
        medico_id = sessao_data.get('medico_id')
        if medico_id:
            # Inverte o mapa para encontrar o nome a partir do ID
            inv_medico_map = {v: k for k, v in medico_map.items()}
            medico_nome = inv_medico_map.get(medico_id)
            if medico_nome:
                combo_medico.set(medico_nome)

        # Preenche os campos das abas
        widgets['resumo'].insert('1.0', sessao_data.get('resumo_sessao') or "")
        widgets['evolucao'].set(sessao_data.get('nivel_evolucao') or "")
        widgets['obs_evolucao'].insert('1.0', sessao_data.get('observacoes_evolucao') or "")
        widgets['plano'].insert('1.0', sessao_data.get('plano_terapeutico') or "")
    else:  # Modo de criação
        entry_data.insert(0, date.today().strftime('%d/%m/%Y'))

    # Botão Salvar
    comando_salvar = lambda: (salvar_alteracoes_sessao(janela_form, sessao_id, widgets) if sessao_id 
                               else salvar_nova_sessao(janela_form, paciente_id, widgets))
    btn_salvar = ttk.Button(
        frame,
        text="Salvar Alterações" if sessao_id else "Salvar Sessão",
        command=comando_salvar
    )
    btn_salvar.pack(side='bottom', pady=(10, 0))

    # Atualiza a lista de sessões quando a janela de formulário é fechada
    janela_pai.wait_window(janela_form)
    callback_atualizar()

def abrir_janela_edicao_sessao(janela_pai, sessao_id, callback_atualizar):
    """Abre o formulário de sessão no modo de edição."""
    # Para editar, não precisamos do paciente_id inicialmente, pois já temos o sessao_id.
    # A função de salvar alterações usará o sessao_id.
    abrir_janela_form_sessao(janela_pai, callback_atualizar=callback_atualizar, sessao_id=sessao_id)

def abrir_janela_prontuario(janela_pai, paciente_id, paciente_nome):
    """Abre a janela do prontuário do paciente com abas para diferentes seções."""
    janela_prontuario = tk.Toplevel(janela_pai)
    janela_prontuario.title(f"Prontuário de {paciente_nome}")
    janela_prontuario.geometry("800x600")
    janela_prontuario.transient(janela_pai)
    janela_prontuario.grab_set()

    # --- Carrega os dados do prontuário ---
    try:
        prontuario_data = database.buscar_ou_criar_prontuario(paciente_id)
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar o prontuário: {e}", parent=janela_prontuario)
        janela_prontuario.destroy()
        return

    prontuario_id = prontuario_data['id']

    # --- Estrutura da Janela ---
    main_frame = ttk.Frame(janela_prontuario, padding=10)
    main_frame.pack(fill='both', expand=True)

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill='both', expand=True, pady=5)

    # --- Aba 1: Informações Gerais ---
    aba_info = ttk.Frame(notebook, padding=10)
    notebook.add(aba_info, text=' Informações Gerais ')

    ttk.Label(aba_info, text="Queixa Principal / Motivo da Consulta:", font=("Helvetica", 10, "bold")).pack(anchor='w')
    txt_queixa = tk.Text(aba_info, height=4, wrap='word'); txt_queixa.pack(fill='x', pady=(0, 10))
    txt_queixa.insert('1.0', prontuario_data.get('queixa_principal') or "")

    ttk.Label(aba_info, text="Histórico Médico Relevante (diagnósticos, alergias, etc.):", font=("Helvetica", 10, "bold")).pack(anchor='w')
    txt_historico = tk.Text(aba_info, height=6, wrap='word'); txt_historico.pack(fill='x', pady=(0, 10))
    txt_historico.insert('1.0', prontuario_data.get('historico_medico_relevante') or "")
    
    ttk.Label(aba_info, text="Informações Adicionais (contato de emergência, observações):", font=("Helvetica", 10, "bold")).pack(anchor='w')
    txt_info_adicional = tk.Text(aba_info, height=4, wrap='word'); txt_info_adicional.pack(fill='x', pady=(0, 10))
    txt_info_adicional.insert('1.0', prontuario_data.get('informacoes_adicionais') or "")

    # --- Aba 2: Anamnese ---
    aba_anamnese = ttk.Frame(notebook, padding=10)
    notebook.add(aba_anamnese, text=' Anamnese ')
    
    ttk.Label(aba_anamnese, text="Anamnese (histórico detalhado do desenvolvimento, familiar, social, etc.):", font=("Helvetica", 10, "bold")).pack(anchor='w')
    txt_anamnese = tk.Text(aba_anamnese, wrap='word'); txt_anamnese.pack(fill='both', expand=True, pady=5)
    txt_anamnese.insert('1.0', prontuario_data.get('anamnese') or "")

    # --- Botão Salvar ---
    def salvar_prontuario():
        try:
            database.atualizar_prontuario(prontuario_id, txt_queixa.get("1.0", "end-1c").strip(), txt_historico.get("1.0", "end-1c").strip(), txt_anamnese.get("1.0", "end-1c").strip(), txt_info_adicional.get("1.0", "end-1c").strip())
            messagebox.showinfo("Sucesso", "Prontuário salvo com sucesso!", parent=janela_prontuario)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível salvar o prontuário: {e}", parent=janela_prontuario)

    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill='x', pady=(10, 0))
    ttk.Button(btn_frame, text="Salvar Prontuário", command=salvar_prontuario).pack(side='right')
    ttk.Button(btn_frame, text="Fechar", command=janela_prontuario.destroy).pack(side='right', padx=10)

class JanelaListaMedicos(tk.Toplevel):
    """Janela para listar e gerenciar todos os médicos, agora como uma classe."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Médicos e Terapeutas Cadastrados")
        self.geometry("800x400")
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.recarregar_lista()

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill='both')

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(expand=True, fill='both', pady=(0, 10))
        
        cols = ('ID', 'Nome Completo', 'Especialidade', 'Contato')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=15)
        self.tree.heading('ID', text='ID'); self.tree.column('ID', width=50, anchor='center')
        self.tree.heading('Nome Completo', text='Nome Completo'); self.tree.column('Nome Completo', width=300)
        self.tree.heading('Especialidade', text='Especialidade'); self.tree.column('Especialidade', width=200)
        self.tree.heading('Contato', text='Contato'); self.tree.column('Contato', width=200)
        self.tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)

        botoes_frame = ttk.Frame(frame)
        botoes_frame.pack(fill='x', side='bottom')
        ttk.Button(botoes_frame, text="Adicionar Novo", command=self.adicionar_novo).pack(side='left', padx=5)
        ttk.Button(botoes_frame, text="Editar Selecionado", command=self.editar_selecionado).pack(side='left', padx=5)
        ttk.Button(botoes_frame, text="Gerenciar Disponibilidade", command=self.gerenciar_disponibilidade).pack(side='left', padx=5)
        ttk.Button(botoes_frame, text="Excluir Selecionado", command=self.excluir_selecionado).pack(side='left', padx=5)

    def recarregar_lista(self):
        """Limpa e recarrega a lista de médicos do banco de dados."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            for medico in database.listar_medicos():
                self.tree.insert("", "end", values=(medico['id'], medico['nome_completo'], medico['especialidade'], medico['contato']))
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar médicos: {e}", parent=self)

    def _get_selected_medico_info(self):
        """Retorna o ID e o nome do médico selecionado na tabela, ou None se ninguém for selecionado."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um médico na lista.", parent=self)
            return None, None
        
        item_values = self.tree.item(selected_item)['values']
        medico_id = item_values[0]
        medico_nome = item_values[1]
        return medico_id, medico_nome

    def adicionar_novo(self):
        """Abre o formulário para adicionar um novo médico."""
        abrir_janela_form_medico(self, self.recarregar_lista)

    def editar_selecionado(self):
        """Abre o formulário para editar o médico selecionado."""
        medico_id, _ = self._get_selected_medico_info()
        if not medico_id:
            return
        abrir_janela_form_medico(self, self.recarregar_lista, medico_id=medico_id)

    def gerenciar_disponibilidade(self):
        """Abre a janela de gerenciamento de disponibilidade para o médico selecionado."""
        medico_id, medico_nome = self._get_selected_medico_info()
        if not medico_id:
            return
        abrir_janela_disponibilidade(self, medico_id, medico_nome)

    def excluir_selecionado(self):
        """Exclui o médico selecionado após confirmação."""
        medico_id, nome_medico = self._get_selected_medico_info()
        if not medico_id:
            return
            
        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja excluir '{nome_medico}'?", parent=self):
            try:
                database.excluir_medico(medico_id)
                self.recarregar_lista()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro de Integridade", f"Não é possível excluir '{nome_medico}', pois ele(a) está associado(a) a sessões existentes.", parent=self)
            except sqlite3.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Erro ao excluir: {e}", parent=self)


class JanelaListaPacientes(tk.Toplevel):
    """
    Janela para listar, buscar e gerenciar todos os pacientes.
    """
    def __init__(self, parent: tk.Tk, callback_atualizar_calendario: Callable):
        super().__init__(parent)
        self.callback_atualizar_calendario = callback_atualizar_calendario

        self.title("Lista de Pacientes Cadastrados")
        self.geometry("950x500") # Aumentado para caber a nova coluna
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self.recarregar_lista()

    def _create_widgets(self):
        """Cria e posiciona todos os widgets da janela."""
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill='both')

        # --- Frame de Busca ---
        busca_frame = ttk.Frame(frame)
        busca_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(busca_frame, text="Buscar por Nome:").pack(side='left', padx=(0, 5))
        self.entry_busca = ttk.Entry(busca_frame, width=40)
        self.entry_busca.pack(side='left', expand=True, fill='x', padx=5)
        self.entry_busca.bind("<Return>", lambda event: self.recarregar_lista())

        ttk.Button(busca_frame, text="Buscar", command=self.recarregar_lista).pack(side='left')
        ttk.Button(busca_frame, text="Limpar", command=self.limpar_busca).pack(side='left', padx=5)

        # --- Tabela (Treeview) ---
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(expand=True, fill='both')
        # Colunas reordenadas para colocar o status ao lado do nome
        cols = ('ID', 'Nome Completo', 'Status Pagamento', 'Idade', 'Nascimento', 'Responsável', 'Telefone', 'Plano de Saúde', 'Valor Padrão')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=15)

        self.tree.heading('ID', text='ID'); self.tree.column('ID', width=40, anchor='center')
        self.tree.heading('Nome Completo', text='Nome'); self.tree.column('Nome Completo', width=200)
        self.tree.heading('Status Pagamento', text='Status'); self.tree.column('Status Pagamento', width=80, anchor='center')
        self.tree.heading('Idade', text='Idade'); self.tree.column('Idade', width=40, anchor='center')
        self.tree.heading('Nascimento', text='Nascimento'); self.tree.column('Nascimento', width=100, anchor='center')
        self.tree.heading('Responsável', text='Responsável'); self.tree.column('Responsável', width=200)
        self.tree.heading('Telefone', text='Telefone'); self.tree.column('Telefone', width=100)
        self.tree.heading('Plano de Saúde', text='Plano de Saúde'); self.tree.column('Plano de Saúde', width=150)
        self.tree.heading('Valor Padrão', text='Valor (R$)'); self.tree.column('Valor Padrão', width=80, anchor='e')

        # Adicionando tag para destacar pacientes com pendências
        self.tree.tag_configure('paciente_pendente', background='#fce5cd') # Laranja claro
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- Botões de Ação Principais ---
        botoes_frame = ttk.Frame(frame)
        botoes_frame.pack(fill='x', side='bottom', pady=(10, 0))
        
        # Botões principais movidos para o menu de contexto para uma UI mais limpa
        ttk.Button(botoes_frame, text="Adicionar Novo Paciente", command=lambda: abrir_janela_cadastro(self, self.recarregar_lista)).pack(side='left')
        ttk.Button(botoes_frame, text="Atualizar Lista", command=self.recarregar_lista).pack(side='right')

        # --- Menu de Contexto ---
        self.menu_contexto = tk.Menu(self.tree, tearoff=0)
        self.menu_contexto.add_command(label="Ver Sessões", command=self.ver_sessoes_selecionado)
        self.menu_contexto.add_command(label="Ver Prontuário", command=self.ver_prontuario_selecionado)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="Quitar Pagamentos Pendentes", command=self.gerenciar_pagamentos)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="Editar Paciente", command=self.editar_selecionado)
        self.menu_contexto.add_command(label="Excluir Paciente", command=self.excluir_selecionado)

        self.tree.bind("<Button-3>", self._mostrar_menu_contexto)

        # --- Evento de clique na célula ---
        self.tree.bind("<Button-1>", self.on_cell_click)

    def recarregar_lista(self):
        termo_busca = self.entry_busca.get().strip()
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            pacientes = database.buscar_pacientes_por_nome(termo_busca) if termo_busca else database.listar_pacientes()
            for paciente in pacientes:
                # Verifica se o paciente tem pendências financeiras
                tem_pendencia = database.verificar_pendencias_paciente(paciente['id'])
                status_pagamento = "Pendente" if tem_pendencia else "Em dia"
                tag = 'paciente_pendente' if tem_pendencia else ''

                idade = calcular_idade(paciente.get('data_nascimento', ''))
                data_nasc_exibicao = formatar_data_para_exibicao(paciente['data_nascimento'])
                # Valores reordenados para corresponder às novas colunas
                valores = (
                    paciente['id'], paciente['nome_completo'], status_pagamento,
                    idade, 
                    data_nasc_exibicao, paciente['nome_responsavel'], 
                    paciente.get('telefone_responsavel') or "",
                    paciente.get('plano_saude_nome') or "Não definido",
                    f"{paciente.get('valor_sessao_padrao', 0.0):.2f}"
                )
                self.tree.insert("", "end", values=valores, tags=(tag,))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao buscar pacientes: {e}", parent=self)

    def limpar_busca(self):
        self.entry_busca.delete(0, 'end')
        self.recarregar_lista()

    def _get_selected_paciente_info(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um paciente.", parent=self)
            return None
        return self.tree.item(selected_item)['values']

    def on_cell_click(self, event):
        """Lida com cliques nas células da tabela, especialmente na coluna de pagamentos."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        column_id = self.tree.identify_column(event.x)
        # Verifica pelo nome do cabeçalho em vez de um índice fixo (mais robusto)
        column_header = self.tree.heading(column_id, "text")
        if column_header == "Status Pagamento":
            self.tree.focus(item_id) # Foca na linha clicada
            paciente_info = self.tree.item(item_id, 'values')
            status_pagamento = paciente_info[2]
            if status_pagamento == 'Pendente':
                self.gerenciar_pagamentos()
            else:
                messagebox.showinfo("Pagamentos", "Este paciente está com os pagamentos em dia.", parent=self)

    def _mostrar_menu_contexto(self, event):
        """Exibe o menu de contexto ao clicar com o botão direito."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            
            # Habilita/desabilita a opção de gerenciar pagamentos
            paciente_info = self.tree.item(item_id, 'values')
            status_pagamento = paciente_info[2] # A 3ª coluna (índice 2) é 'Status Pagamento'
            if status_pagamento == 'Pendente':
                self.menu_contexto.entryconfig("Quitar Pagamentos Pendentes", state="normal")
            else:
                self.menu_contexto.entryconfig("Quitar Pagamentos Pendentes", state="disabled")
            
            self.menu_contexto.post(event.x_root, event.y_root)

    def editar_selecionado(self):
        paciente_info = self._get_selected_paciente_info()
        if paciente_info:
            paciente_id = paciente_info[0]
            abrir_janela_edicao(self, paciente_id, self.recarregar_lista)

    def ver_sessoes_selecionado(self):
        paciente_info = self._get_selected_paciente_info()
        if paciente_info:
            paciente_id, paciente_nome = paciente_info[0], paciente_info[1]
            abrir_janela_sessoes(self, paciente_id, paciente_nome, self.callback_atualizar_calendario)

    def ver_prontuario_selecionado(self):
        paciente_info = self._get_selected_paciente_info()
        if paciente_info:
            paciente_id, paciente_nome = paciente_info[0], paciente_info[1]
            abrir_janela_prontuario(self, paciente_id, paciente_nome)

    def gerenciar_pagamentos(self):
        paciente_info = self._get_selected_paciente_info()
        if paciente_info:
            paciente_id, paciente_nome = paciente_info[0], paciente_info[1]
            abrir_janela_pagamentos_pendentes(self, paciente_id, paciente_nome, self.recarregar_lista)

    def excluir_selecionado(self):
        paciente_info = self._get_selected_paciente_info()
        if paciente_info:
            paciente_id, paciente_nome = paciente_info[0], paciente_info[1]
            if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir '{paciente_nome}'?", parent=self):
                try:
                    database.excluir_paciente(paciente_id)
                    messagebox.showinfo("Sucesso", "Paciente excluído com sucesso.", parent=self)
                    self.recarregar_lista()
                except sqlite3.Error as e:
                    messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao excluir: {e}", parent=self)

# --- Funções de Gerenciamento de Usuários (Admin) ---

def abrir_janela_cadastro_usuario(janela_pai, callback_atualizar):
    """Abre uma janela para cadastrar um novo usuário."""
    janela_cad_user = tk.Toplevel(janela_pai)
    janela_cad_user.title("Cadastrar Usuário")
    janela_cad_user.geometry("400x250")
    janela_cad_user.transient(janela_pai)
    janela_cad_user.grab_set()

    frame = ttk.Frame(janela_cad_user, padding=20)
    frame.pack(fill='both', expand=True)

    ttk.Label(frame, text="Nome de Usuário:").grid(row=0, column=0, sticky='w', pady=2)
    entry_user = ttk.Entry(frame, width=30)
    entry_user.grid(row=1, column=0, sticky='ew', pady=(0, 10))
    entry_user.focus_set()

    ttk.Label(frame, text="Senha:").grid(row=2, column=0, sticky='w', pady=2)
    entry_pass = ttk.Entry(frame, width=30, show="*")
    entry_pass.grid(row=3, column=0, sticky='ew', pady=(0, 10))

    ttk.Label(frame, text="Confirmar Senha:").grid(row=4, column=0, sticky='w', pady=2)
    entry_pass_confirm = ttk.Entry(frame, width=30, show="*")
    entry_pass_confirm.grid(row=5, column=0, sticky='ew', pady=(0, 10))

    ttk.Label(frame, text="Nível de Acesso:").grid(row=6, column=0, sticky='w', pady=2)
    combo_nivel = ttk.Combobox(frame, values=['terapeuta', 'admin'], state='readonly')
    combo_nivel.grid(row=7, column=0, sticky='ew')
    combo_nivel.set('terapeuta')

    def salvar_novo_usuario():
        user, p1, p2, nivel = entry_user.get().strip(), entry_pass.get(), entry_pass_confirm.get(), combo_nivel.get()
        if not (user and p1 and p2 and nivel):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios.", parent=janela_cad_user); return
        if p1 != p2:
            messagebox.showerror("Erro", "As senhas não coincidem.", parent=janela_cad_user); return
        if len(p1) < 6:
            messagebox.showwarning("Senha Fraca", "A senha deve ter no mínimo 6 caracteres.", parent=janela_cad_user); return
        
        try:
            database.adicionar_usuario(user, p1, nivel)
            messagebox.showinfo("Sucesso", f"Usuário '{user}' criado com sucesso.", parent=janela_cad_user)
            janela_cad_user.destroy()
            callback_atualizar()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=janela_cad_user)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Erro ao criar usuário: {e}", parent=janela_cad_user)

    ttk.Button(frame, text="Salvar", command=salvar_novo_usuario).grid(row=8, column=0, sticky='e', pady=15)

def abrir_janela_gerenciar_usuarios(janela_principal):
    """Abre a janela de gerenciamento de usuários para o admin."""
    janela_users = tk.Toplevel(janela_principal)
    janela_users.title("Gerenciamento de Usuários")
    janela_users.geometry("600x400")
    janela_users.transient(janela_principal)
    janela_users.grab_set()

    frame = ttk.Frame(janela_users, padding="10")
    frame.pack(expand=True, fill='both')

    tree_frame = ttk.Frame(frame)
    tree_frame.pack(expand=True, fill='both', pady=(0, 10))
    cols = ('ID', 'Nome de Usuário', 'Nível de Acesso')
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings')

    tree.heading('ID', text='ID'); tree.column('ID', width=50, anchor='center')
    tree.heading('Nome de Usuário', text='Nome de Usuário'); tree.column('Nome de Usuário', width=250)
    tree.heading('Nível de Acesso', text='Nível de Acesso'); tree.column('Nível de Acesso', width=150, anchor='center')
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky='ns')
    tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)

    def recarregar_lista():
        for i in tree.get_children(): tree.delete(i)
        try:
            for user in database.listar_usuarios():
                tree.insert("", "end", values=(user['id'], user['nome_usuario'], user['nivel_acesso']))
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar usuários: {e}", parent=janela_users)

    def excluir_selecionado():
        selected_item = tree.focus()
        if not selected_item: return
        
        user_id = tree.item(selected_item)['values'][0]
        user_nome = tree.item(selected_item)['values'][1]

        if user_id == USUARIO_LOGADO['id']:
            messagebox.showerror("Ação Inválida", "Você não pode excluir o seu próprio usuário.", parent=janela_users)
            return

        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja excluir o usuário '{user_nome}'?", parent=janela_users):
            try:
                database.excluir_usuario(user_id)
                recarregar_lista()
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao excluir usuário: {e}", parent=janela_users)

    botoes_frame = ttk.Frame(frame)
    botoes_frame.pack(fill='x', side='bottom')
    ttk.Button(botoes_frame, text="Adicionar Novo", command=lambda: abrir_janela_cadastro_usuario(janela_users, recarregar_lista)).pack(side='left', padx=5)
    ttk.Button(botoes_frame, text="Excluir Selecionado", command=excluir_selecionado).pack(side='left', padx=5)

    recarregar_lista()
    
class JanelaGerenciarPlanos(tk.Toplevel):
    """Janela para adicionar e remover planos de saúde."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gerenciar Planos de Saúde")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self.recarregar_lista_planos()

    def _create_widgets(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill='both', expand=True)

        # --- Frame para adicionar novo plano ---
        add_frame = ttk.LabelFrame(frame, text="Adicionar Novo Plano", padding=10)
        add_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(add_frame, text="Nome do Plano:").pack(side='left', padx=(0, 5))
        self.entry_nome_plano = ttk.Entry(add_frame, width=30)
        self.entry_nome_plano.pack(side='left', expand=True, fill='x')
        ttk.Button(add_frame, text="Adicionar", command=self._adicionar_novo_plano).pack(side='left', padx=5)

        # --- Tabela de planos existentes ---
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        cols = ('ID', 'Nome')
        self.tree_planos = ttk.Treeview(tree_frame, columns=cols, show='headings')
        self.tree_planos.heading('ID', text='ID'); self.tree_planos.column('ID', width=50, anchor='center')
        self.tree_planos.heading('Nome', text='Nome do Plano'); self.tree_planos.column('Nome', width=300)
        self.tree_planos.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree_planos.yview)
        self.tree_planos.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        # --- Botão de Excluir ---
        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill='x', pady=(10, 0))
        ttk.Button(bottom_frame, text="Excluir Plano Selecionado", command=self._excluir_plano_selecionado).pack(side='left')

    def _adicionar_novo_plano(self):
        nome = self.entry_nome_plano.get().strip()
        if not nome:
            messagebox.showwarning("Campo Vazio", "O nome do plano não pode ser vazio.", parent=self)
            return
        try:
            database.adicionar_plano_saude(nome)
            self.entry_nome_plano.delete(0, 'end')
            self.recarregar_lista_planos()
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível adicionar o plano: {e}", parent=self)

    def recarregar_lista_planos(self):
        """Limpa e recarrega a lista de planos de saúde."""
        for i in self.tree_planos.get_children():
            self.tree_planos.delete(i)
        try:
            for plano in database.listar_planos_saude():
                self.tree_planos.insert("", "end", values=(plano['id'], plano['nome']))
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar planos: {e}", parent=self)

    def _excluir_plano_selecionado(self):
        selected_item = self.tree_planos.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Selecione um plano para excluir.", parent=self)
            return
        
        plano_id, plano_nome = self.tree_planos.item(selected_item)['values']

        # Prevenção para não excluir planos essenciais
        if plano_nome.lower() in ['particular', 'outro']:
            messagebox.showerror("Ação Inválida", f"O plano '{plano_nome}' não pode ser excluído.", parent=self)
            return

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o plano '{plano_nome}'?", parent=self):
            try:
                database.excluir_plano_saude(plano_id)
                self.recarregar_lista_planos()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro de Integridade", f"Não é possível excluir o plano '{plano_nome}', pois ele está sendo utilizado por um ou mais pacientes.", parent=self)
            except sqlite3.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Não foi possível excluir o plano: {e}", parent=self)

def abrir_janela_principal():

    root = tk.Tk()
    root.title("Sistema de Clínica - Início")
    root.geometry("900x600") # Aumentei o tamanho para caber o dashboard

    # --- Layout com Frames ---
    top_frame = tk.Frame(root, pady=10)
    top_frame.pack(fill='x', padx=10, anchor='n')
    tk.Label(top_frame, text="Sistema de Acompanhamento Terapêutico", font=("Helvetica", 16, "bold")).pack(side='left', expand=True)
    if USUARIO_LOGADO:
        user_info = f"Usuário: {USUARIO_LOGADO['nome_usuario']} ({USUARIO_LOGADO['nivel_acesso']})"
        tk.Label(top_frame, text=user_info, font=("Helvetica", 9)).pack(side='right')

    main_content_frame = tk.Frame(root)
    main_content_frame.pack(fill='both', expand=True, padx=10, pady=10)

    # Frame da Esquerda para os botões
    left_frame = tk.Frame(main_content_frame, width=200)
    left_frame.pack(side='left', fill='y', padx=(0, 10))
    left_frame.pack_propagate(False) # Impede que o frame encolha para o tamanho dos botões

    # Frame da Direita para o dashboard (calendário + agenda)
    right_frame = tk.Frame(main_content_frame)
    right_frame.pack(side='right', fill='both', expand=True)

    # --- Dashboard (no frame da direita) ---
    
    # Calendário
    cal_frame = ttk.Frame(right_frame)
    cal_frame.pack(fill='x', pady=(0, 10))
    hoje = date.today()
    cal = Calendar(cal_frame, selectmode='day', year=hoje.year, month=hoje.month, day=hoje.day,
                   locale='pt_BR', date_pattern='dd/mm/y')
    cal.pack(fill="x", expand=True)
    cal.tag_config('sessao_marcada', background='lightblue', foreground='black')

    # Tabela de Agendamentos do Dia
    agenda_frame = ttk.LabelFrame(right_frame, text="Agendamentos do Dia")
    agenda_frame.pack(fill='both', expand=True)
    cols = ('horario', 'paciente', 'terapeuta')
    tree_agenda = ttk.Treeview(agenda_frame, columns=cols, show='headings')
    tree_agenda.heading('horario', text='Horário'); tree_agenda.column('horario', width=100, anchor='center')
    tree_agenda.heading('paciente', text='Paciente'); tree_agenda.column('paciente', width=200)
    tree_agenda.heading('terapeuta', text='Terapeuta'); tree_agenda.column('terapeuta', width=200)
    tree_agenda.pack(fill='both', expand=True)

    # --- Funções e Botões (que dependem do calendário) ---

    def atualizar_eventos_calendario(calendario):
        """Busca as datas com sessões e as marca no calendário."""
        # Limpa todos os eventos antigos para não duplicar
        calendario.calevent_remove('all')
        
        datas_sessoes = database.listar_datas_sessoes()
        for data_str in datas_sessoes:
            try:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                # Cria um evento naquela data com uma tag específica
                calendario.calevent_create(data_obj, 'Sessão Agendada', tags='sessao_marcada')
            except (ValueError, TypeError):
                continue # Ignora datas em formato inválido

    # --- Botões de Ação (no frame da esquerda) ---
    botoes = [
        ("Agenda Geral", lambda: abrir_janela_agenda_geral(root)),
        ("Cadastrar Paciente", lambda: abrir_janela_cadastro(root, lambda: atualizar_eventos_calendario(cal))),
        ("Controle de Pagamentos", lambda: abrir_janela_controle_pagamentos(root)),
        ("Gestão Financeira", lambda: FluxoCaixaWindow(root)),
        ("Listar Pacientes", lambda: JanelaListaPacientes(root, lambda: atualizar_eventos_calendario(cal)))
    ]

    # Botões visíveis apenas para o administrador
    if USUARIO_LOGADO and USUARIO_LOGADO['nivel_acesso'] == 'admin':
        botoes.extend([
            ("Backup do Sistema", lambda: realizar_backup(root)),
            ("Gerenciar Médicos", lambda: JanelaListaMedicos(root)),
            ("Gerenciar Planos", lambda: JanelaGerenciarPlanos(root)),
            ("Gerenciar Usuários", lambda: abrir_janela_gerenciar_usuarios(root)),
            ("Restaurar Backup", lambda: realizar_restauracao(root))
        ])

    # Ordena os botões em ordem alfabética e os exibe
    botoes.sort(key=lambda x: x[0])
    for texto, comando in botoes:
        tk.Button(left_frame, text=texto, font=("Helvetica", 11), command=comando).pack(pady=5, fill='x')

    def atualizar_dashboard():
        """Função que atualiza todos os componentes do dashboard."""
        atualizar_eventos_calendario(cal)
        atualizar_agenda_do_dia()
        messagebox.showinfo("Atualização", "Dashboard atualizado com sucesso!", parent=root)

    def atualizar_agenda_do_dia(event=None):
        """Busca e exibe as sessões para o dia selecionado no calendário."""
        for i in tree_agenda.get_children():
            tree_agenda.delete(i)
        
        data_selecionada = cal.get_date()
        data_db = formatar_data_para_db(data_selecionada)
        
        sessoes = database.listar_sessoes_por_data(data_db)
        for sessao in sessoes:
            horario = f"{sessao['hora_inicio_sessao'] or ''} - {sessao['hora_fim_sessao'] or ''}"
            tree_agenda.insert("", "end", values=(horario, sessao['paciente_nome'], sessao['medico_nome']))

    # --- Binds e Carregamento Inicial ---
    cal.bind("<<CalendarSelected>>", atualizar_agenda_do_dia)

    btn_atualizar_dash = tk.Button(left_frame, text="Atualizar Dashboard", font=("Helvetica", 11), command=atualizar_dashboard)
    btn_atualizar_dash.pack(side='bottom', pady=10, fill='x')

    # Carregamento inicial
    atualizar_eventos_calendario(cal)
    atualizar_agenda_do_dia() # Carrega a agenda para o dia de hoje

    root.mainloop()

def abrir_janela_login():
    """Abre a janela de login inicial do sistema."""
    login_window = tk.Tk()
    login_window.title("Login - Sistema de Clínica")
    login_window.geometry("350x180")
    login_window.resizable(True, True)

    # Centraliza a janela na tela
    window_width, window_height = 350, 180
    screen_width = login_window.winfo_screenwidth()
    screen_height = login_window.winfo_screenheight()
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
    login_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    frame = ttk.Frame(login_window, padding="20")
    frame.pack(expand=True, fill='both')

    ttk.Label(frame, text="Nome de Usuário:").pack(anchor='w')
    entry_user = ttk.Entry(frame, width=30)
    entry_user.pack(fill='x', pady=(0, 10))
    entry_user.focus_set()

    ttk.Label(frame, text="Senha:").pack(anchor='w')
    entry_pass = ttk.Entry(frame, width=30, show="*")
    entry_pass.pack(fill='x', pady=(0, 15))

    def tentar_login():
        usuario = entry_user.get().strip()
        senha = entry_pass.get().strip()
        if not usuario or not senha:
            messagebox.showerror("Erro", "Usuário e senha são obrigatórios.", parent=login_window)
            return

        usuario_valido = database.verificar_usuario(usuario, senha)
        if usuario_valido:
            global USUARIO_LOGADO
            USUARIO_LOGADO = usuario_valido
            login_window.destroy()
            abrir_janela_principal()
        else:
            messagebox.showerror("Falha no Login", "Nome de usuário ou senha incorretos.", parent=login_window)

    entry_pass.bind("<Return>", lambda event: tentar_login())
    ttk.Button(frame, text="Login", command=tentar_login).pack(fill='x')
    login_window.mainloop()

def main():
    """Função principal que inicializa o DB e chama a tela de login."""
    try:
        database.inicializar_banco_de_dados()
    except Exception as e:
        root_error = tk.Tk(); root_error.withdraw()
        messagebox.showerror("Erro Crítico", f"Erro ao inicializar o banco de dados:\n\n{e}")
        return
    abrir_janela_login()

if __name__ == "__main__":
    main()