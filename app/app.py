from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
import psycopg2 #pip install psycopg2 
import psycopg2.extras
from werkzeug.utils import secure_filename
import os
import json
import matplotlib
import matplotlib.ticker as ticker
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from datetime import datetime
from threading import Thread
import pandas as pd

# Configurações postgresql
DB_HOST = "localhost"
#DB_HOST = "10.0.2.15"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_PORT = "5433"


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
 
conn = psycopg2.connect(
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

app = Flask(__name__)
app.secret_key = 'chave_secreta'

app.config['UPLOAD_FOLDER'] = '/home/allan/pibiti/plataforma_gestao_agropecuaria/app/static/uploads'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, nome, senha, nome_completo, vinculo, acessos):
        self.id = id
        self.nome = nome
        self.senha = senha
        self.nome_completo = nome_completo
        self.vinculo = vinculo
        self.acessos = acessos
        
@login_manager.user_loader
def load_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, nome, senha, nome_completo, vinculo, acessos FROM api.usuarios WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    print(user_data)
    if user_data:
        user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5])
        return user
    else:
        return None


@app.route('/')
def index():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM api.experimento;"
    cur.execute(s)
    list_exps = cur.fetchall()
    for exp in list_exps:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d %H:%M:%S')
    print(list_exps)
    return render_template('index.html', experimentos=list_exps, user=current_user)

@app.route('/sobre')
def sobre():
    return render_template('sobre.html', user=current_user)

#------------------------------------------------------------USUÁRIO---------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------


@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'GET':
        user_id = current_user.id
        nome = current_user.nome
        senha = current_user.senha
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        return render_template('perfil.html', user_id=user_id, nome=nome, senha=senha, nome_completo=nome_completo, vinculo=vinculo, user=current_user)
    elif request.method == 'POST':
        print('a')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user() 
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('index', user=current_user))

@app.route('/login',  methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        cur = conn.cursor()
        cur.execute("SELECT id FROM api.usuarios WHERE nome = %s and senha = %s", (nome, senha))        
        user_id = cur.fetchone() 
        if user_id:
            user = load_user(user_id)
            login_user(user)  
            flash('Login bem sucedido!', 'success')
            return redirect(url_for('perfil', user=current_user))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
            return redirect(url_for('login', user=current_user))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('cadastro.html', user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.usuarios (nome, senha, nome_completo, vinculo) VALUES (%s, %s, %s, %s)", (nome, senha, nome_completo, vinculo))
        conn.commit()
        print("Registro POST recebido")
        print("Nome de usuário:", nome)
        print("Senha:", senha)
        flash('Registro bem sucedido! Faça login para continuar.', 'success')

        return redirect(url_for('login', user=current_user))
    
@app.route('/editar-perfil', methods=['GET', 'POST'])
def editar_perfil():
    if request.method == 'GET':
        nome = current_user.nome
        senha = current_user.senha
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        return render_template('perfil-editar.html', nome=nome, senha=senha, nome_completo=nome_completo, vinculo=vinculo, user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']
        cur = conn.cursor()
        cur.execute("UPDATE api.usuarios SET nome=%s, senha=%s, nome_completo=%s, vinculo=%s WHERE id=%s", (nome, senha, nome_completo, vinculo, current_user.id))
        conn.commit()
        return redirect(url_for('perfil', user=current_user))
    
@app.route('/deletar-perfil', methods=['GET'])
def deletar_perfil():
    cur = conn.cursor()
    cur.execute("DELETE FROM api.usuarios WHERE id=%s", (current_user.id,))
    conn.commit()
    return redirect(url_for('logout', user=current_user))




#------------------------------------------------------------FORMULARIO---------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------------------

@app.route('/solicitacoes_experimento/<int:id>')
@login_required
def solicitacoes_experimento(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM api.solicitacoes WHERE experimento_id = %s", (id,))
    solicitacoes = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (id,))
    experimento = cur.fetchone()
    return render_template('experimento-solicitacoes.html', solicitacoes=solicitacoes, experimento_id = id, experimento=experimento, user=current_user)

@app.route('/recusar-solicitacao/<int:id>')
def recusar_solicitacao(id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.solicitacoes WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('meus_experimentos',  user=current_user))

@app.route('/aceitar-solicitacao/<int:id>')
def aceitar_solicitacao(id):
    cur = conn.cursor()
    cur.execute("SELECT experimento_id, solicitante_id, criador_experimento_id FROM api.solicitacoes WHERE id = %s", (id,))
    result = cur.fetchone()
    experimento_id = result[0]
    solicitante_id = result[1]

    cur.execute("UPDATE api.usuarios SET acessos = array_append(acessos, %s) WHERE id = %s", (experimento_id, solicitante_id))
    conn.commit()
    
    cur.execute("UPDATE api.experimento SET disponivel_para = array_append(disponivel_para, %s) WHERE id = %s", (solicitante_id, experimento_id))
    conn.commit()
    
    print(f"UPDATE FEITO exp{experimento_id} e user{solicitante_id}")
    cur.execute("DELETE FROM api.solicitacoes WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('meus_experimentos', user=current_user))


@app.route('/formulario_requisicao/<int:id>', methods=['GET', 'POST'])
@login_required
def formulario_requisicao(id):
    if request.method == 'POST':
        nome_completo = request.form['nome']
        vinculo = request.form['vinculo']
        if vinculo == 'outro':
            vinculo = request.form['outro_vinculo']
        projeto = request.form['projeto']
        orientador = request.form['orientador']
        tipos_dados = request.form['tipos_dados']
        if tipos_dados == 'outro':
            tipos_dados = request.form['outro_tipos_dados']
        info_adicionais = request.form['info_adicionais']
        compromisso1 = 'compromisso1' in request.form
        compromisso2 = 'compromisso2' in request.form
        compromisso3 = 'compromisso3' in request.form
        compromisso4 = 'compromisso4' in request.form
        compromisso5 = 'compromisso5' in request.form
        compromisso6 = 'compromisso6' in request.form
        
        solicitante_id = current_user.id
        experimento_id = id
        
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO api.solicitacoes 
                (solicitante_id, experimento_id,nome_completo, vinculo, projeto, orientador, tipos_dados, info_adicionais, compromisso1, compromisso2, compromisso3, compromisso4, compromisso5, compromisso6) 
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (solicitante_id, experimento_id, nome_completo, vinculo, projeto, orientador, tipos_dados, info_adicionais, compromisso1, compromisso2, compromisso3, compromisso4, compromisso5, compromisso6))
        
        conn.commit()
        return redirect(url_for('index', user=current_user))
    else:
        return render_template('formulario.html', experimento_id = id,user=current_user)
    
#------------------------------------------------------------EXPERIMENTOS---------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    
@app.route('/inserir-experimento', methods=['GET', 'POST'])
@login_required
def inserir_experimento():
    if request.method == 'GET':
        return render_template('experimento-inserir.html', user=current_user)
    elif request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        categoria = request.form['categoria']
        outra_categoria = request.form['outra_categoria']
        if outra_categoria:
            categoria = outra_categoria
        localizacao = request.form['localizacao']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.experimento (titulo, descricao, categoria, localizacao, cadastrado_por) VALUES (%s, %s, %s, %s, %s)", (titulo, descricao, categoria, localizacao, current_user.id))
        conn.commit()
        print("Registro POST recebido")
        print("titulo:", titulo)
        print("categoria:", categoria)
        flash('Registro bem sucedido! Faça login para continuar.', 'success')
        return redirect(url_for('meus_experimentos', user=current_user))
    
@app.route('/detalhes-experimento/<int:experimento_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_experimento(experimento_id):
    if request.method == 'GET':
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        print(experimento)
        return render_template('experimento-editar.html', experimento=experimento, experimento_id=experimento_id, user=current_user)
    elif request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        categoria = request.form['categoria']
        outra_categoria = request.form['outra_categoria']
        if outra_categoria:
            categoria = outra_categoria
        localizacao = request.form['localizacao']
        cur = conn.cursor()
        cur.execute("UPDATE api.experimento SET titulo=%s, descricao=%s, categoria=%s, localizacao=%s WHERE id=%s", (titulo, descricao, categoria, localizacao,experimento_id))
        conn.commit()
        return redirect(url_for('detalhes_experimento', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/deletar', methods=['GET'])
@login_required
def deletar_experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.experimento WHERE id = %s", (experimento_id,))
    return redirect(url_for('meus_experimentos', user=current_user))
    
@app.route('/experimento/<int:experimento_id>')
@login_required
def experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('index-experimento.html', experimento = experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>')
@login_required
def detalhes_experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('experimento-detalhes.html', experimento = experimento, user=current_user)

@app.route('/meus-experimentos')
@login_required
def meus_experimentos():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM api.experimento WHERE cadastrado_por = %s", (current_user.id,))
    experimentos_criados = cur.fetchall()
    for exp in experimentos_criados:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d às %H:%M')
    
    cur.execute("SELECT * FROM api.experimento WHERE %s = ANY (disponivel_para)", (current_user.id,))
    experimentos_disponiveis = cur.fetchall()
    for exp in experimentos_disponiveis:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d às %H:%M')

    return render_template('meus-experimentos.html', experimentos_criados=experimentos_criados, experimentos_disponiveis=experimentos_disponiveis, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/anexos', methods=['GET', 'POST'])
@login_required
def experimento_anexos(experimento_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(caminho_arquivo)
                
                cur = conn.cursor()
                cur.execute("INSERT INTO api.anexos_experimento (experimento_id, nome_do_arquivo, caminho_do_arquivo, descricao) VALUES (%s, %s, %s, %s)", (experimento_id, nome_arquivo, caminho_arquivo, descricao))
                conn.commit()
                
                return redirect(url_for('experimento_anexos', experimento_id=experimento_id, user=current_user))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.anexos_experimento WHERE experimento_id = %s", (experimento_id,))
        anexos = cur.fetchall()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('experimento-anexos.html', experimento_id=experimento_id, experimento=experimento,anexos=anexos, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/download')
@login_required
def download_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    caminho_do_arquivo = resultado[0] if resultado else None

    if caminho_do_arquivo:
        return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(caminho_do_arquivo)    )
    else:
        return 'Arquivo não encontrado', 404

@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/deletar')
@login_required
def deletar_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()

    cur.execute("DELETE FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    conn.commit()
    
    if resultado:
        caminho_do_arquivo = resultado[0]
        if os.path.exists(caminho_do_arquivo):
            os.remove(caminho_do_arquivo)


        return redirect(url_for('experimento_anexos', experimento_id=experimento_id, user=current_user))
    else:
        return 'Arquivo não encontrado', 404

@app.route('/detalhes-experimento/<int:experimento_id>/url', methods=['GET','POST'])
@login_required
def experimento_url(experimento_id):
    if request.method == 'POST':    
        url = request.form['url']
        nome_url = request.form['nome']
        descricao = request.form['descricao_url']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.urls_experimento (experimento_id, url, nome_url, descricao) VALUES (%s, %s, %s, %s)", (experimento_id, url, nome_url, descricao))
        conn.commit()
    
        return redirect(url_for('experimento_url', experimento_id=experimento_id, user=current_user))
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.urls_experimento WHERE experimento_id = %s", (experimento_id,))
        urls = cur.fetchall()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('experimento-urls.html', experimento_id=experimento_id, experimento=experimento, urls=urls, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/url/<int:url_id>/deletar')
@login_required
def deletar_url_experimento(experimento_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_experimento WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('experimento_url', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo', methods=['GET'])
@login_required
def experimento_dispositivos(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE experimento_id = %s", (experimento_id,))
    dispositivos = cur.fetchall()
    print(dispositivos)
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('experimento-dispositivos.html', experimento_id=experimento_id, experimento=experimento,dispositivos=dispositivos, user=current_user)


import json

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/inserir', methods=['GET', 'POST'])
@login_required
def experimento_dispositivos_inserir(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        mac_address = request.form['mac_address']
        colunas = request.form.getlist('coluna[]')

        colunas_detalhes = []
        for i in range(0, len(colunas), 4):
            coluna = {
                'nome': colunas[i],
                'descricao': colunas[i+1],
                'tipo': colunas[i+2],
                'unidade': colunas[i+3]
            }
            colunas_detalhes.append(coluna)
        colunas_json = json.dumps(colunas_detalhes)
        
        
        ativo = 'false'
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.dispositivo (experimento_id, nome, mac_address, descricao, cadastrado_por, ativo, colunas) VALUES (%s, %s, %s, %s, %s, %s, %s)", (experimento_id, nome, mac_address, descricao, current_user.id, ativo, [colunas_json]))
        conn.commit()
        
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('experimento-dispositivo-inserir.html', experimento_id=experimento_id, experimento=experimento, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/editar', methods=['GET', 'POST'])
@login_required
def experimento_dispositivo_editar(experimento_id, dispositivo_id):
    if request.method == 'GET':
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
        dispositivo = cur.fetchone()
        if dispositivo:
            dispositivo_json = {
                'id': dispositivo_id,
                'nome': dispositivo[1],
                'descricao': dispositivo[4],
                'mac_address': dispositivo[5],
                'ativo': dispositivo[2],
                'colunas': []
            }
            if dispositivo[8]:  # Verifica se o campo de colunas não está vazio
                string=dispositivo[8][0]
                lista = json.loads(string)  # Converte a string JSON em objeto Python
                for item in lista:
                    dispositivo_json['colunas'].append(item)

            print(dispositivo_json)
            return render_template('experimento-dispositivo-editar.html', dispositivo=dispositivo_json, experimento_id=experimento_id, dispositivo_id=dispositivo_id, user=current_user)
        else:
            # Lidar com o caso em que o dispositivo não foi encontrado no banco de dados
            return "Dispositivo não encontrado."

    elif request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        mac_address = request.form['mac_address']
        colunas = request.form.getlist('coluna[]')

        colunas_detalhes = []
        for i in range(0, len(colunas), 4):
            coluna = {
                'nome': colunas[i],
                'descricao': colunas[i+1],
                'tipo': colunas[i+2],
                'unidade': colunas[i+3]
            }
            colunas_detalhes.append(coluna)
        colunas_json = json.dumps(colunas_detalhes)
        ativo = 'false'

        
        cur = conn.cursor()
        cur.execute("UPDATE api.dispositivo SET nome=%s, descricao=%s, mac_address=%s, ativo=%s, colunas=%s WHERE id=%s", (nome, descricao, mac_address, ativo, [colunas_json], dispositivo_id))
        conn.commit()
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta', methods=['GET'])
@login_required
def experimento_dispositivo_coleta(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    dispositivo = cur.fetchone()
    if dispositivo:
        dispositivo_json = {
            'id': dispositivo_id,
            'nome': dispositivo[1],
            'descricao': dispositivo[4],
            'mac_address': dispositivo[5],
            'ativo': dispositivo[2],
            'colunas': []
        }
        if dispositivo[8]:  # Verifica se o campo de colunas não está vazio
            string=dispositivo[8][0]
            lista = json.loads(string)  # Converte a string JSON em objeto Python
            for item in lista:
                dispositivo_json['colunas'].append(item)

        cur = conn.cursor()
        cur.execute("SELECT * FROM api.coleta WHERE dispositivo_id = %s", (dispositivo_id,))
        coletas = cur.fetchall()
        
        """varia = 1
        for coluna in dispositivo_json["colunas"]:
            experimento_dispositivo_grafico(dispositivo_id, varia, coluna)
            varia = varia+1"""
        
        print(dispositivo_json)
        return render_template('experimento-dispositivo-coleta.html', experimento_id=experimento_id, dispositivo=dispositivo_json, dispositivo_id=dispositivo_id, coletas=coletas, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/deletar')
@login_required
def experimento_dispositivo_deletar(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/deletar')
@login_required
def experimento_dispositivo_coleta_deletar(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.coleta WHERE dispositivo_id = %s", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))


#@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/grafico/<int:coluna_id>/<coluna>')
def experimento_dispositivo_grafico(dispositivo_id, coluna_id, coluna):
    coluna_dict = coluna
    print(coluna_dict)
    cur = conn.cursor()
    cur.execute("SELECT a%s, gerado_em  FROM api.coleta WHERE dispositivo_id = %s", (coluna_id, dispositivo_id,))
    coletas = cur.fetchall()
    
    datas = [coleta[1] for coleta in coletas]
    tipo_coluna = coluna_dict.get('tipo')
    if tipo_coluna == 'REAL' or tipo_coluna == 'real':
        valores = []
        for coleta in coletas:
            try:
                valor = float(coleta[0])
            except ValueError:
                valor = None 
            valores.append(valor)
    else:
        valores = [coleta[0] for coleta in coletas]

    # Converter as datas para um formato adequado para plotagem
    datas_plot = [datetime.strptime(str(data), '%Y-%m-%d %H:%M:%S.%f') for data in datas]


    plt.figure(figsize=(18, 8))
    
    # Plotar o gráfico
    plt.plot(datas_plot, valores, marker='', linestyle='-')
    plt.xlabel('Data da Coleta')
    plt.ylabel('Valor da Coleta (' + coluna_dict['unidade'] + ')')
    plt.title('Gráfico da Coluna ' + coluna_dict['nome'] + ':\n' + coluna_dict['descricao'])
    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=25))

    
    #plt.text(0.5, 0.5, coluna_dict['descricao'], verticalalignment='bottom', horizontalalignment='center',  transform=plt.gca().transAxes, fontsize=10)
    
    plt.tight_layout()
    # Salvar o gráfico como uma imagem
    imagem_grafico = f'/home/allan/pibiti/font-test/static/graficos/grafico-{dispositivo_id}-{coluna_dict["nome"]}.png'
    
    plt.savefig(imagem_grafico)
    plt.close()
    
    # Enviar a imagem como resposta
    #return send_file(imagem_grafico, mimetype='image/png')
    return

#------------------------------------------------------------ETAPAS-------------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

@app.route('/detalhes-experimento/<int:experimento_id>/etapas', methods=['GET'])
@login_required
def etapas_experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem", (experimento_id,))
    etapas = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('etapas-detalhes.html', experimento_id=experimento_id, experimento=experimento,etapas=etapas, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/inserir', methods=['GET','POST'])
@login_required
def inserir_etapa(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        status = request.form['status']
        experimento_id = experimento_id
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.etapa (nome, descricao, status, experimento_id) VALUES (%s, %s, %s, %s)", (nome, descricao, status, experimento_id))
        conn.commit()
        flash('Etapa inserida com sucesso!', 'success')
        return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))
    else:
        return render_template('etapa-inserir.html', experimento_id=experimento_id, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/ordem', methods=['GET'])
@login_required
def ordem_etapa(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem;", (experimento_id,))
    etapas = cur.fetchall()
    return render_template('etapas-ordem.html', etapas=etapas, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/atualizar_ordem', methods=['POST'])
@login_required
def atualizar_ordem(experimento_id):
    data = request.get_json()
    nova_ordem = data.get('novaOrdem')
    
    cur = conn.cursor()
    
    for item in nova_ordem:
        idx = item.get('index')
        texto = item.get('texto')
        txt = texto.split()
        id = txt[-1]
        cur.execute("UPDATE api.etapa SET ordem = %s WHERE id = %s;", (idx, id))
    conn.commit()
    
    return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos', methods=['GET', 'POST'])
@login_required
def etapa_anexos(experimento_id, etapa_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(caminho_arquivo)
                
                cur = conn.cursor()
                cur.execute("INSERT INTO api.anexos_etapa (etapa_id, nome_do_arquivo, caminho_do_arquivo, descricao) VALUES (%s, %s, %s, %s)", (etapa_id, nome_arquivo, caminho_arquivo, descricao))
                conn.commit()
                
                return redirect(url_for('etapa_anexos', experimento_id=experimento_id, etapa_id=etapa_id, user=current_user))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.anexos_etapa WHERE etapa_id = %s", (etapa_id,))
        anexos = cur.fetchall()
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapa = cur.fetchone()
        return render_template('etapa-anexos.html', experimento_id=experimento_id, etapa_id=etapa_id, etapa=etapa,anexos=anexos, user=current_user)
            
@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_etapa(experimento_id, etapa_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        status = request.form['status']
        experimento_id = experimento_id
        
        cur = conn.cursor()
        cur.execute("UPDATE api.etapa SET nome = %s, descricao = %s, status = %s WHERE id = %s", (nome, descricao, status, etapa_id,))
        conn.commit()
        flash('Etapa editada com sucesso!', 'success')
        return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapas = cur.fetchall()
        print(etapas[0])
        return render_template('etapa-editar.html', experimento_id=experimento_id,etapa=etapas[0], user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/deletar', methods=['GET'])
@login_required
def deletar_etapa(experimento_id, etapa_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.etapa WHERE id = %s", (etapa_id,))
    return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/detalhes-experimento/etapas/<int:etapa_id>/anexos/<int:anexo_id>/download')
@login_required
def download_anexo(etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    caminho_do_arquivo = resultado[0] if resultado else None

    if caminho_do_arquivo:
        return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(caminho_do_arquivo)    )
    else:
        return 'Arquivo não encontrado', 404


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos/<int:anexo_id>/deletar')
@login_required
def deletar_anexos_etapa(experimento_id,etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()

    cur.execute("DELETE FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    conn.commit()
    
    if resultado:
        caminho_do_arquivo = resultado[0]
        if os.path.exists(caminho_do_arquivo):
            os.remove(caminho_do_arquivo)


        return redirect(url_for('etapa_anexos', etapa_id=etapa_id, experimento_id=experimento_id, user=current_user))
    else:
        return 'Arquivo não encontrado', 404


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/url', methods=['GET','POST'])
@login_required
def etapa_url(experimento_id, etapa_id):
    if request.method == 'POST':
        url = request.form['url']
        nome_url = request.form['nome']
        descricao = request.form['descricao_url']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.urls_etapa (etapa_id, url, nome_url, descricao) VALUES (%s, %s, %s, %s)", (etapa_id, url, nome_url, descricao))
        conn.commit()
        
        return redirect(url_for('etapa_url', experimento_id=experimento_id, etapa_id=etapa_id, user=current_user))
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.urls_etapa WHERE etapa_id = %s", (etapa_id,))
        urls = cur.fetchall()
        print(urls)
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapa = cur.fetchone()
        return render_template('etapa-urls.html', experimento_id=experimento_id, etapa_id=etapa_id, etapa=etapa, urls=urls, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/url/<int:url_id>/deletar')
@login_required
def deletar_url_etapa(experimento_id,etapa_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_etapa WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('etapa_url', etapa_id=etapa_id, experimento_id=experimento_id, user=current_user))

if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5001,threaded=True)
    app.run(debug=True, threaded=True, port=5001)