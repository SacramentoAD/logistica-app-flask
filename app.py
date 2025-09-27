import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2 # Adaptado para PostgreSQL
from psycopg2.extras import RealDictCursor # Para acessar colunas por nome

app = Flask(__name__)
# Chave secreta para segurança das sessões (mude isso!)
app.config['SECRET_KEY'] = 'uma_chave_secreta_muito_forte_aqui_12345' 

# --- Configuração do Banco de Dados PostgreSQL ---
# Esta variável será definida pelo Render/Railway no ambiente de nuvem
DATABASE_URL = os.environ.get('DATABASE_URL', 'dbname=logistica user=postgres password=senha host=localhost') 

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # Usamos RealDictCursor para retornar as linhas como dicionários (mais fácil de acessar)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        # Em ambiente local, se falhar, tenta iniciar o banco de dados
        # Essa lógica é mais complexa e depende do seu setup local.
        # Na nuvem, o serviço gerencia.
        return None
    
# --- Funções de Inicialização (Cria as Tabelas se não existirem) ---
def init_db():
    conn = get_db_connection()
    if conn is None: return

    cursor = conn.cursor()
    
    # 1. Tabela Caminhões
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS caminhoes (
            id SERIAL PRIMARY KEY,
            placa VARCHAR(10) NOT NULL UNIQUE,
            motorista VARCHAR(100) NOT NULL,
            telefone VARCHAR(20),
            ci VARCHAR(50),
            motorista_obs TEXT,
            status VARCHAR(50) NOT NULL,
            observacao TEXT,
            foto VARCHAR(255)
        )
    """)
    
    # 2. Tabela Opções de Status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_opcoes (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) UNIQUE NOT NULL
        )
    """)

    # 3. Insere Status Padrões
    default_status = ["Disponível", "Ocupado", "Logística Reversa", "Manutenção"]
    for status in default_status:
        try:
            cursor.execute("INSERT INTO status_opcoes (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (status,))
        except Exception as e:
            print(f"Erro ao inserir status: {e}")

    conn.commit()
    conn.close()

# --- Rotas da Aplicação (Substituem as Funções do Tkinter) ---

# Rota Principal: Listagem e Tabela (Substitui atualizar_tabela)
@app.route('/')
def index():
    init_db() # Garante que as tabelas existem
    conn = get_db_connection()
    if conn is None:
        return "Erro: Não foi possível conectar ao banco de dados.", 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM caminhoes ORDER BY id DESC")
    caminhoes = cursor.fetchall()

    cursor.execute("SELECT nome FROM status_opcoes")
    status_opcoes = [row['nome'] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('index.html', caminhoes=caminhoes, status_opcoes=status_opcoes)

# Cadastro/Edição de Caminhão
@app.route('/cadastro', methods=('GET', 'POST'))
def cadastro():
    if request.method == 'POST':
        placa = request.form['placa']
        motorista = request.form['motorista']
        telefone = request.form.get('telefone', '')
        ci = request.form.get('ci', '')
        motorista_obs = request.form.get('motorista_obs', '')
        
        # NOTE: Gerenciar upload de FOTO é complexo em Flask.
        # Por simplicidade, mantemos o campo 'foto' como um PATH de texto por agora.
        foto = request.form.get('foto', '') 

        if not placa or not motorista:
            flash('Placa e Motorista são campos obrigatórios!', 'error')
            return redirect(url_for('index'))
            
        conn = get_db_connection()
        if conn is None:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('index'))
            
        try:
            conn.cursor().execute("""
                INSERT INTO caminhoes (placa, motorista, telefone, ci, motorista_obs, status, foto)
                VALUES (%s, %s, %s, %s, %s, 'Disponível', %s)
            """, (placa, motorista, telefone, ci, motorista_obs, foto))
            conn.commit()
            flash('Caminhão cadastrado com sucesso!', 'success')
        except psycopg2.errors.UniqueViolation:
            flash(f'Erro: Caminhão com a placa {placa} já existe!', 'error')
            conn.rollback()
        except Exception as e:
            flash(f'Erro ao cadastrar: {e}', 'error')
            conn.rollback()
        finally:
            conn.close()
            
        return redirect(url_for('index'))
    
    # Se for GET, retorna o formulário, mas neste caso, o formulário está em index.html
    return redirect(url_for('index'))

# Atualização de Status/Observação (Substitui salvar_alteracoes)
@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    status = request.form.get('status')
    observacao = request.form.get('observacao')

    conn = get_db_connection()
    if conn is None:
        flash('Erro de conexão com o banco de dados.', 'error')
        return redirect(url_for('index'))
        
    try:
        conn.cursor().execute("""
            UPDATE caminhoes SET status = %s, observacao = %s
            WHERE id = %s
        """, (status, observacao, id))
        conn.commit()
        flash('Status e Observação atualizados!', 'success')
    except Exception as e:
        flash(f'Erro ao atualizar: {e}', 'error')
        conn.rollback()
    finally:
        conn.close()
        
    return redirect(url_for('index'))

# --- Inicia a Aplicação ---
if __name__ == '__main__':
    init_db()
    # Roda em 0.0.0.0 para ser acessível na rede local durante testes
    app.run(host='0.0.0.0', port=5000, debug=True)