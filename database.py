import sqlite3
import hashlib # Para criptografar senhas

DB_FILE = 'clinica.db'

# --- Funções de Segurança ---

def hash_senha(senha):
    """Gera um hash SHA-256 para a senha, garantindo que não seja armazenada em texto plano."""
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

# --- Inicialização e Migração ---

def inicializar_banco_de_dados():
    """
    Cria as tabelas se não existirem e garante que o schema da tabela 'sessoes'
    esteja atualizado, adicionando colunas que faltam. Deve ser chamada no início do app.
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # 1. Criar tabela de pacientes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            data_nascimento TEXT NOT NULL, -- Armazenado como YYYY-MM-DD
            nome_responsavel TEXT NOT NULL
        )
        """)

        # Migração para adicionar a coluna de telefone do responsável, se não existir
        cursor.execute("PRAGMA table_info(pacientes)")
        colunas_pacientes = [coluna[1] for coluna in cursor.fetchall()]
        if 'telefone_responsavel' not in colunas_pacientes:
            print("Atualizando schema: Adicionando coluna 'telefone_responsavel' à tabela 'pacientes'...")
            cursor.execute("ALTER TABLE pacientes ADD COLUMN telefone_responsavel TEXT")
        
        # Migração para adicionar a coluna de plano de saúde
        if 'plano_saude_id' not in colunas_pacientes:
            print("Atualizando schema: Adicionando coluna 'plano_saude_id' à tabela 'pacientes'...")
            # Adicionamos a referência à tabela que será criada a seguir
            cursor.execute("ALTER TABLE pacientes ADD COLUMN plano_saude_id INTEGER REFERENCES planos_saude(id)")

        # Migração para adicionar a coluna de valor padrão da sessão
        if 'valor_sessao_padrao' not in colunas_pacientes:
            print("Atualizando schema: Adicionando coluna 'valor_sessao_padrao' à tabela 'pacientes'...")
            cursor.execute("ALTER TABLE pacientes ADD COLUMN valor_sessao_padrao REAL DEFAULT 0.0")

        # Migração para adicionar a coluna valor_sessao na tabela sessoes
        cursor.execute("PRAGMA table_info(sessoes)")
        if 'valor_sessao' not in [col[1] for col in cursor.fetchall()]:
            cursor.execute("ALTER TABLE sessoes ADD COLUMN valor_sessao REAL DEFAULT 0.0")


        # 2. Criar tabela de medicos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            especialidade TEXT,
            contato TEXT
        )
        """)

        # 3. Criar tabela de sessões (se não existir)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_sessao TEXT NOT NULL, -- Armazenado como YYYY-MM-DD            
            resumo_sessao TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id) ON DELETE CASCADE
        )
        """)
 
        # 4. Migração e Criação da tabela de disponibilidade dos médicos
        # Esta lógica robusta garante que a tabela sempre terá o schema mais recente.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='disponibilidade_medico'")
        table_exists = cursor.fetchone()
        if table_exists:
            # A tabela existe. Vamos verificar se ela tem o schema antigo.
            cursor.execute("PRAGMA table_info(disponibilidade_medico)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'dia_semana' in columns:
                # Schema antigo detectado. Apagamos a tabela para recriá-la.
                print("Schema antigo detectado para 'disponibilidade_medico'. Atualizando...")
                cursor.execute("DROP TABLE disponibilidade_medico")
 
        # Cria a tabela (se não existir, ou se foi apagada por ser antiga)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS disponibilidade_medico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id INTEGER NOT NULL,
            data_disponivel TEXT NOT NULL, -- Formato YYYY-MM-DD
            hora_inicio TEXT NOT NULL, -- Formato HH:MM
            hora_fim TEXT NOT NULL, -- Formato HH:MM
            FOREIGN KEY (medico_id) REFERENCES medicos (id) ON DELETE CASCADE
        )
        """)
        # 5. Migração de Schema para 'sessoes'
        cursor.execute("PRAGMA table_info(sessoes)")
        colunas_existentes = [coluna[1] for coluna in cursor.fetchall()]

        colunas_necessarias = {
            "nivel_evolucao": "TEXT",
            "observacoes_evolucao": "TEXT",
            "plano_terapeutico": "TEXT",
            "medico_id": "INTEGER", # Adiciona a coluna para referenciar o médico
            "hora_inicio_sessao": "TEXT",
            "hora_fim_sessao": "TEXT"
        }
        
        # A coluna 'valor_sessao' foi movida para a tabela 'pacientes'.
        # Apenas 'status_pagamento' permanece aqui.
        colunas_financeiras = {"status_pagamento": "TEXT"}
        if 'valor_sessao' in colunas_existentes:
             print("Schema antigo detectado: Removendo 'valor_sessao' da tabela 'sessoes'. (Movido para 'pacientes')")
             # SQLite não tem um DROP COLUMN simples, então esta é uma abordagem complexa que não faremos aqui. Apenas garantimos que a nova coluna não seja adicionada.

        for coluna, tipo in colunas_necessarias.items():
            if coluna not in colunas_existentes:
                print(f"Atualizando schema: Adicionando coluna '{coluna}' à tabela 'sessoes'...")
                cursor.execute(f"ALTER TABLE sessoes ADD COLUMN {coluna} {tipo}")

        # 6. Criar tabela de prontuários
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prontuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL UNIQUE,
            queixa_principal TEXT,
            historico_medico_relevante TEXT,
            anamnese TEXT,
            informacoes_adicionais TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id) ON DELETE CASCADE
        )
        """)

        # 7. Criar tabela de usuários
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            nivel_acesso TEXT NOT NULL DEFAULT 'terapeuta' -- Ex: 'admin', 'terapeuta'
        )
        """)

        # 8. Criar usuário admin padrão se não existir nenhum
        cursor.execute("SELECT 1 FROM usuarios WHERE nivel_acesso = 'admin'")
        if not cursor.fetchone():
            nome_admin_padrao = 'admin'
            senha_admin_padrao = 'admin123'
            senha_hashed = hash_senha(senha_admin_padrao)
            cursor.execute(
                "INSERT INTO usuarios (nome_usuario, senha_hash, nivel_acesso) VALUES (?, ?, ?)",
                (nome_admin_padrao, senha_hashed, 'admin')
            )
            print("="*50)
            print("NENHUM USUÁRIO ADMIN ENCONTRADO. UM PADRÃO FOI CRIADO:")
            print(f"  Usuário: {nome_admin_padrao}\n  Senha:   {senha_admin_padrao}")
            print("="*50)

        # 9. Criar tabela de despesas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL -- Formato YYYY-MM-DD
        )
        """)

        # 10. Criar tabela de Planos de Saúde e popular com valores iniciais
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS planos_saude (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
        """)
        # Verifica se a tabela está vazia antes de popular
        cursor.execute("SELECT COUNT(id) FROM planos_saude")
        if cursor.fetchone()[0] == 0:
            print("Populando tabela 'planos_saude' com valores iniciais...")
            planos_iniciais = [
                ('Particular',), ('Unimed',), ('Hapvida',), ('Bradesco Saúde',),
                ('Amil',), ('SulAmérica Saúde',), ('NotreDame Intermédica',), ('Outro',)
            ]
            cursor.executemany("INSERT INTO planos_saude (nome) VALUES (?)", planos_iniciais)


        print("Banco de dados pronto.")

# --- Funções de Pacientes ---

def adicionar_paciente(nome, data_nasc, responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao):
    """Adiciona um novo paciente ao banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pacientes (nome_completo, data_nascimento, nome_responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao) VALUES (?, ?, ?, ?, ?, ?)",
            (nome, data_nasc, responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao)
        )

def listar_pacientes():
    """Retorna uma lista de todos os pacientes cadastrados, ordenados por nome."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row  # Retorna resultados como dicionários
        cursor = conn.cursor()
        cursor.execute("SELECT p.id, p.nome_completo, p.data_nascimento, p.nome_responsavel, p.telefone_responsavel, p.valor_sessao_padrao, ps.nome as plano_saude_nome FROM pacientes p LEFT JOIN planos_saude ps ON p.plano_saude_id = ps.id ORDER BY p.nome_completo")
        # Converte os objetos Row para dicionários para desacoplar do sqlite3
        return [dict(row) for row in cursor.fetchall()]

def buscar_paciente_por_id(paciente_id):
    """Busca um paciente específico pelo seu ID."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_completo, data_nascimento, nome_responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao FROM pacientes WHERE id = ?", (paciente_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def atualizar_paciente(paciente_id, nome, data_nasc, responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao):
    """Atualiza os dados de um paciente existente."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE pacientes
            SET nome_completo = ?,
                data_nascimento = ?,
                nome_responsavel = ?,
                telefone_responsavel = ?,
                plano_saude_id = ?,
                valor_sessao_padrao = ?
            WHERE id = ?
            """,
            (nome, data_nasc, responsavel, telefone_responsavel, plano_saude_id, valor_sessao_padrao, paciente_id)
        )

def excluir_paciente(paciente_id):
    """Exclui um paciente do banco de dados pelo seu ID."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))

def buscar_pacientes_por_nome(termo_busca):
    """Busca pacientes cujo nome completo contenha o termo de busca (case-insensitive)."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT p.id, p.nome_completo, p.data_nascimento, p.nome_responsavel, p.telefone_responsavel, p.valor_sessao_padrao, ps.nome as plano_saude_nome FROM pacientes p LEFT JOIN planos_saude ps ON p.plano_saude_id = ps.id WHERE lower(p.nome_completo) LIKE ? ORDER BY p.nome_completo",
            ('%' + termo_busca.lower() + '%',)
        )
        return [dict(row) for row in cursor.fetchall()]

# --- Funções de Médicos ---

def adicionar_medico(nome, especialidade, contato):
    """Adiciona um novo médico ao banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO medicos (nome_completo, especialidade, contato) VALUES (?, ?, ?)",
            (nome, especialidade, contato)
        )

def listar_medicos():
    """Retorna uma lista de todos os médicos cadastrados."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_completo, especialidade, contato FROM medicos ORDER BY nome_completo")
        return [dict(row) for row in cursor.fetchall()]

def buscar_medico_por_id(medico_id):
    """Busca um médico específico pelo seu ID."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_completo, especialidade, contato FROM medicos WHERE id = ?", (medico_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def atualizar_medico(medico_id, nome, especialidade, contato):
    """Atualiza os dados de um médico existente."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE medicos SET nome_completo = ?, especialidade = ?, contato = ? WHERE id = ?",
                       (nome, especialidade, contato, medico_id))

def excluir_medico(medico_id):
    """Exclui um médico do banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medicos WHERE id = ?", (medico_id,))

# --- Funções de Disponibilidade de Médicos ---

def adicionar_disponibilidade(medico_id, data_disponivel, hora_inicio, hora_fim):
    """Adiciona um novo horário de disponibilidade para um médico."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO disponibilidade_medico (medico_id, data_disponivel, hora_inicio, hora_fim) VALUES (?, ?, ?, ?)",
            (medico_id, data_disponivel, hora_inicio, hora_fim)
        )

def listar_disponibilidade_por_data(medico_id, data_disponivel):
    """Retorna os horários de um médico para uma data específica."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, hora_inicio, hora_fim FROM disponibilidade_medico WHERE medico_id = ? AND data_disponivel = ? ORDER BY hora_inicio",
            (medico_id, data_disponivel)
        )
        return [dict(row) for row in cursor.fetchall()]

def listar_datas_disponiveis_por_mes(medico_id, ano, mes):
    """Retorna as datas únicas com disponibilidade para um médico em um dado mês/ano."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # O formato YYYY-MM% garante que pegamos todos os dias do mês
        cursor.execute("SELECT DISTINCT data_disponivel FROM disponibilidade_medico WHERE medico_id = ? AND data_disponivel LIKE ?",
                       (medico_id, f"{ano}-{mes:02d}-%"))
        return [row[0] for row in cursor.fetchall()]

def excluir_disponibilidade(disponibilidade_id):
    """Exclui um horário de disponibilidade específico pelo seu ID."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM disponibilidade_medico WHERE id = ?", (disponibilidade_id,))

# --- Funções de Prontuário ---

def buscar_ou_criar_prontuario(paciente_id):
    """
    Busca o prontuário de um paciente. Se não existir, cria um em branco e o retorna.
    """
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Tenta buscar o prontuário
        cursor.execute("SELECT * FROM prontuarios WHERE paciente_id = ?", (paciente_id,))
        prontuario = cursor.fetchone()
        
        if prontuario:
            return dict(prontuario)
        else:
            # Se não existir, cria um novo
            cursor.execute("INSERT INTO prontuarios (paciente_id) VALUES (?)", (paciente_id,))
            conn.commit()
            # Busca novamente para retornar o registro completo com o ID
            cursor.execute("SELECT * FROM prontuarios WHERE paciente_id = ?", (paciente_id,))
            novo_prontuario = cursor.fetchone()
            return dict(novo_prontuario)

def atualizar_prontuario(prontuario_id, queixa, historico, anamnese, info_adicional):
    """Atualiza os dados de um prontuário existente."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE prontuarios SET queixa_principal = ?, historico_medico_relevante = ?, anamnese = ?, informacoes_adicionais = ? WHERE id = ?""",
            (queixa, historico, anamnese, info_adicional, prontuario_id)
        )

# --- Funções de Usuários ---

def adicionar_usuario(nome_usuario, senha, nivel_acesso):
    """Adiciona um novo usuário ao banco de dados. Lança ValueError se o usuário já existir."""
    senha_hashed = hash_senha(senha)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (nome_usuario, senha_hash, nivel_acesso) VALUES (?, ?, ?)",
                (nome_usuario, senha_hashed, nivel_acesso)
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"O nome de usuário '{nome_usuario}' já existe.")

def listar_usuarios():
    """Retorna uma lista de todos os usuários cadastrados."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_usuario, nivel_acesso FROM usuarios ORDER BY nome_usuario")
        return [dict(row) for row in cursor.fetchall()]

def atualizar_senha_usuario(usuario_id, nova_senha):
    """Atualiza a senha de um usuário específico."""
    nova_senha_hashed = hash_senha(nova_senha)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (nova_senha_hashed, usuario_id))

def excluir_usuario(usuario_id):
    """Exclui um usuário do banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

def verificar_usuario(nome_usuario, senha):
    """Verifica as credenciais do usuário. Retorna dados do usuário se for válido, senão None."""
    senha_hashed = hash_senha(senha)
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nome_usuario, nivel_acesso FROM usuarios WHERE nome_usuario = ? AND senha_hash = ?",
            (nome_usuario, senha_hashed)
        )
        usuario = cursor.fetchone()
        return dict(usuario) if usuario else None

# --- Funções de Sessões ---

def adicionar_sessao(paciente_id, medico_id, data, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano):
    """Adiciona uma nova sessão para um paciente."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Busca o valor padrão da sessão do paciente
        cursor.execute("SELECT valor_sessao_padrao FROM pacientes WHERE id = ?", (paciente_id,))
        result = cursor.fetchone()
        valor_padrao = result[0] if result else 0.0

        cursor.execute(
            """INSERT INTO sessoes (paciente_id, medico_id, data_sessao, hora_inicio_sessao, hora_fim_sessao,
                                  resumo_sessao, nivel_evolucao, observacoes_evolucao, plano_terapeutico, valor_sessao,
                                  status_pagamento)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paciente_id, medico_id, data, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano, valor_padrao, 'Pendente')
        )

def listar_sessoes_por_paciente(paciente_id):
    """Retorna uma lista de todas as sessões de um paciente, ordenadas pela data mais recente."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.data_sessao, s.hora_inicio_sessao, s.nivel_evolucao, s.resumo_sessao, m.nome_completo as medico_nome, s.valor_sessao, s.status_pagamento
            FROM sessoes s
            LEFT JOIN medicos m ON s.medico_id = m.id
            WHERE s.paciente_id = ? 
            ORDER BY s.data_sessao DESC, s.hora_inicio_sessao DESC
            """,
            (paciente_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def buscar_sessao_por_id(sessao_id):
    """Busca uma sessão específica com todos os seus detalhes pelo ID."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Juntando com pacientes e medicos para obter nomes
        cursor.execute("""
            SELECT 
                s.*, 
                p.nome_completo as paciente_nome,
                m.nome_completo as medico_nome
            FROM sessoes s
            JOIN pacientes p ON s.paciente_id = p.id
            LEFT JOIN medicos m ON s.medico_id = m.id
            WHERE s.id = ?
        """, (sessao_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def atualizar_sessao(sessao_id, medico_id, data, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano):
    """Atualiza os dados de uma sessão existente."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE sessoes SET 
                    medico_id = ?,
                    data_sessao = ?,
                    hora_inicio_sessao = ?,
                    hora_fim_sessao = ?,
                    resumo_sessao = ?,
                    nivel_evolucao = ?,
                    observacoes_evolucao = ?,
                    plano_terapeutico = ?
               WHERE id = ?""",
            (medico_id, data, hora_inicio, hora_fim, resumo, evolucao, obs_evolucao, plano, sessao_id)
        )

def atualizar_financeiro_sessao(sessao_id, valor, status_pagamento):
    """Atualiza apenas os campos financeiros de uma sessão específica."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessoes SET valor_sessao = ?, status_pagamento = ? WHERE id = ?",
            (valor, status_pagamento, sessao_id)
        )

def excluir_sessao(sessao_id):
    """Exclui uma sessão do banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE id = ?", (sessao_id,))

def listar_datas_sessoes():
    """Retorna uma lista de datas únicas (YYYY-MM-DD) que possuem sessões agendadas."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT data_sessao FROM sessoes")
        # Retorna uma lista de strings de data, ex: ['2023-10-26', '2023-10-27']
        return [row[0] for row in cursor.fetchall()]

def listar_sessoes_por_medico_e_data(medico_id, data_db):
    """Retorna os horários de início das sessões já agendadas para um médico em uma data."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT hora_inicio_sessao FROM sessoes WHERE medico_id = ? AND data_sessao = ?",
            (medico_id, data_db)
        )
        return [row[0] for row in cursor.fetchall()]

def verificar_conflito_sessao(medico_id, data_db, hora_inicio, hora_fim, sessao_id_excluir=None):
    """
    Verifica se já existe uma sessão para um médico que conflite com o novo horário.
    A lógica de conflito é: (StartA < EndB) and (EndA > StartB)
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        query = """
            SELECT 1 FROM sessoes 
            WHERE medico_id = ? AND data_sessao = ? 
            AND hora_inicio_sessao < ? AND hora_fim_sessao > ?
        """
        params = [medico_id, data_db, hora_fim, hora_inicio]
        if sessao_id_excluir:
            query += " AND id != ?"
            params.append(sessao_id_excluir)
        
        cursor.execute(query, params)
        return cursor.fetchone() is not None

def listar_sessoes_por_data(data_db):
    """Retorna as sessões de uma data específica com nome do paciente e médico."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.hora_inicio_sessao, s.hora_fim_sessao, p.nome_completo as paciente_nome, m.nome_completo as medico_nome
            FROM sessoes s
            JOIN pacientes p ON s.paciente_id = p.id
            LEFT JOIN medicos m ON s.medico_id = m.id
            WHERE s.data_sessao = ?
            ORDER BY s.hora_inicio_sessao
        """, (data_db,))
        return [dict(row) for row in cursor.fetchall()]

def listar_disponibilidade_geral_por_data(data_db):
    """Retorna a disponibilidade de todos os médicos para uma data específica."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.hora_inicio, d.hora_fim, m.nome_completo as medico_nome
            FROM disponibilidade_medico d
            JOIN medicos m ON d.medico_id = m.id
            WHERE d.data_disponivel = ?
            ORDER BY m.nome_completo, d.hora_inicio
        """, (data_db,))
        return [dict(row) for row in cursor.fetchall()]

# --- Funções Financeiras ---

def adicionar_despesa(descricao, valor, data_db):
    """Adiciona uma nova despesa ao banco de dados."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO despesas (descricao, valor, data) VALUES (?, ?, ?)",
            (descricao, valor, data_db)
        )

def listar_despesas_por_periodo(data_inicio_db, data_fim_db):
    """Retorna uma lista de todas as despesas em um período."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM despesas WHERE data BETWEEN ? AND ? ORDER BY data DESC",
            (data_inicio_db, data_fim_db)
        )
        return [dict(row) for row in cursor.fetchall()]

def listar_receitas_por_periodo(data_inicio_db, data_fim_db):
    """Retorna uma lista de todas as receitas (sessões pagas) em um período."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.data_sessao, s.valor_sessao, p.nome_completo as paciente_nome, m.nome_completo as medico_nome
            FROM sessoes s
            JOIN pacientes p ON s.paciente_id = p.id
            LEFT JOIN medicos m ON s.medico_id = m.id
            WHERE s.status_pagamento = 'Pago' AND s.data_sessao BETWEEN ? AND ?
            ORDER BY s.data_sessao DESC
        """, (data_inicio_db, data_fim_db))
        return [dict(row) for row in cursor.fetchall()]

def listar_planos_saude():
    """Retorna uma lista de todos os planos de saúde cadastrados."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM planos_saude ORDER BY nome")
        return [dict(row) for row in cursor.fetchall()]