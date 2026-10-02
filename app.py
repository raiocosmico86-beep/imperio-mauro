from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = "mauro_mr_robot_2024"
DB = "banco.db"

# ============================================
# MODO MANUTENÇÃO
# ============================================
MODO_MANUTENCAO = False

@app.before_request
def checar_manutencao():
    rotas_livres = ["/login", "/manutencao", "/static/favicon.svg"]
    if request.path.startswith("/static/"):
        return
    if request.path in rotas_livres:
        return
    if session.get("adm"):
        return
    if MODO_MANUTENCAO:
        return render_template("manutencao.html"), 503

# ============================================
# UPLOAD DE IMAGENS
# ============================================
UPLOAD_LOJAS = "static/uploads/lojas"
UPLOAD_PRODUTOS = "static/uploads/produtos"
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_LOJAS, exist_ok=True)
os.makedirs(UPLOAD_PRODUTOS, exist_ok=True)

def extensao_ok(nome_arquivo):
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS

def validar_imagem(arquivo):
    """Retorna (ok, mensagem_erro)."""
    if not arquivo or arquivo.filename == "":
        return False, "A imagem é obrigatória."
    if not extensao_ok(arquivo.filename):
        return False, "Formato inválido. Use PNG, JPG, JPEG, GIF ou WEBP."
    return True, None

def salvar_imagem(arquivo, pasta):
    ext = arquivo.filename.rsplit(".", 1)[1].lower()
    nome_unico = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(pasta, nome_unico)
    arquivo.save(caminho)
    return f"/{caminho}"

# ============================================
# BANCO
# ============================================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS lojas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            dono TEXT,
            imagem TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loja_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            descricao TEXT,
            imagem TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO admins (usuario, senha) VALUES ('admin', '1234')")
    conn.commit()
    conn.close()

# ============================================
# ROTAS
# ============================================
@app.route("/")
def index():
    busca = request.args.get("busca", "").strip()
    categoria_id = request.args.get("categoria", "").strip()
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    if busca and categoria_id:
        c.execute("SELECT * FROM lojas WHERE nome LIKE ? AND categoria_id = ?", (f"%{busca}%", categoria_id))
    elif busca:
        c.execute("SELECT * FROM lojas WHERE nome LIKE ?", (f"%{busca}%",))
    elif categoria_id:
        c.execute("SELECT * FROM lojas WHERE categoria_id = ?", (categoria_id,))
    else:
        c.execute("SELECT * FROM lojas")
    
    lojas = c.fetchall()
    
    c.execute("SELECT id, nome, icone FROM categorias ORDER BY nome")
    categorias = c.fetchall()
    
    conn.close()
    return render_template("index.html", lojas=lojas, busca=busca, categorias=categorias, categoria_atual=categoria_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE usuario=? AND senha=?", (usuario, senha))
        adm = c.fetchone()
        conn.close()
        if adm:
            session["adm"] = usuario
            return redirect(url_for("painel"))
        return render_template("login.html", erro="Login inválido!")
    return render_template("login.html")

@app.route("/painel", methods=["GET", "POST"])
def painel():
    if "adm" not in session:
        return redirect(url_for("login"))

    erro = None
    if request.method == "POST":
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        dono = request.form["dono"]
        arquivo = request.files.get("imagem")

        ok, msg = validar_imagem(arquivo)
        if not ok:
            erro = msg
        else:
            imagem = salvar_imagem(arquivo, UPLOAD_LOJAS)
            categoria_id = request.form.get("categoria_id") or None
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO lojas (nome, descricao, dono, imagem, categoria_id) VALUES (?, ?, ?, ?, ?)",
                      (nome, descricao, dono, imagem, categoria_id))
            conn.commit()
            conn.close()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM lojas")
    lojas = c.fetchall()
    c.execute("SELECT id, nome, icone FROM categorias ORDER BY nome")
    categorias = c.fetchall()
    conn.close()
    return render_template("painel.html", lojas=lojas, categorias=categorias, erro=erro)

@app.route("/loja/<int:loja_id>")
def ver_loja(loja_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM lojas WHERE id=?", (loja_id,))
    loja = c.fetchone()
    if loja is None:
        conn.close()
        return render_template("404.html"), 404
    c.execute("SELECT * FROM produtos WHERE loja_id=? ORDER BY id DESC", (loja_id,))
    produtos = c.fetchall()
    conn.close()
    return render_template("loja.html", loja=loja, produtos=produtos)

@app.route("/loja/<int:loja_id>/produto/novo", methods=["GET", "POST"])
def novo_produto(loja_id):
    if "adm" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM lojas WHERE id=?", (loja_id,))
    loja = c.fetchone()
    if loja is None:
        conn.close()
        return render_template("404.html"), 404

    erro = None
    if request.method == "POST":
        nome = request.form["nome"]
        preco = float(request.form["preco"])
        descricao = request.form["descricao"]
        arquivo = request.files.get("imagem")

        ok, msg = validar_imagem(arquivo)
        if not ok:
            erro = msg
        else:
            imagem = salvar_imagem(arquivo, UPLOAD_PRODUTOS)
            c.execute("INSERT INTO produtos (loja_id, nome, preco, descricao, imagem) VALUES (?, ?, ?, ?, ?)",
                      (loja_id, nome, preco, descricao, imagem))
            conn.commit()
            conn.close()
            return redirect(url_for("ver_loja", loja_id=loja_id))

    conn.close()
    return render_template("novo_produto.html", loja=loja, erro=erro)
@app.route("/produto/<int:produto_id>")

def ver_produto(produto_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.nome, p.preco, p.descricao, p.imagem, p.loja_id,
               l.nome, l.dono, l.imagem
        FROM produtos p
        JOIN lojas l ON l.id = p.loja_id
        WHERE p.id = ?
    """, (produto_id,))
    produto = c.fetchone()

    # Busca produtos relacionados da mesma loja
    if produto:
        c.execute("""
            SELECT id, nome, preco, imagem
            FROM produtos
            WHERE loja_id = ? AND id != ?
            ORDER BY RANDOM()
            LIMIT 4
        """, (produto[5], produto_id))
        relacionados = c.fetchall()
    else:
        relacionados = []

    c.execute("""
        SELECT a.nota, a.comentario, a.criado_em, cl.nome
        FROM avaliacoes a
        JOIN clientes cl ON cl.id = a.cliente_id
        WHERE a.produto_id = ?
        ORDER BY a.criado_em DESC
    """, (produto_id,))
    avaliacoes = c.fetchall()
    
    c.execute("SELECT AVG(nota), COUNT(*) FROM avaliacoes WHERE produto_id=?", (produto_id,))
    media_row = c.fetchone()
    if media_row and media_row[0]:
        media = round(media_row[0], 1)
        total_aval = media_row[1]
    else:
        media = 0
        total_aval = 0
    
    minha_aval = None
    if cliente_logado():
        c.execute("SELECT nota, comentario FROM avaliacoes WHERE produto_id=? AND cliente_id=?",
                  (produto_id, session["cliente_id"]))
        minha_aval = c.fetchone()

    conn.close()

    if produto is None:
        return render_template("404.html"), 404

    if avaliacoes is None:
        avaliacoes = []
    if relacionados is None:
        relacionados = []

    return render_template("produto_detalhe.html", produto=produto, relacionados=relacionados,
                           avaliacoes=avaliacoes, media=media, total_aval=total_aval,
                           minha_aval=minha_aval)

@app.route("/produto/<int:produto_id>/deletar", methods=["POST"])
def deletar_produto(produto_id):
    if "adm" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT loja_id FROM produtos WHERE id=?", (produto_id,))
    resultado = c.fetchone()
    if resultado is None:
        conn.close()
        return render_template("404.html"), 404
    loja_id = resultado[0]
    c.execute("DELETE FROM produtos WHERE id=?", (produto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("ver_loja", loja_id=loja_id))



# ============================================
# LOGIN DE CLIENTE
# ============================================

def cliente_logado():
    return session.get("cliente_id") is not None

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro_cliente():
    if cliente_logado():
        return redirect(url_for("minha_conta"))
    erro = None
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        confirma = request.form["confirma"]
        if len(senha) < 6:
            erro = "A senha precisa ter pelo menos 6 caracteres."
        elif senha != confirma:
            erro = "As senhas nao conferem."
        elif "@" not in email or "." not in email:
            erro = "Email invalido."
        else:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT id FROM clientes WHERE email=?", (email,))
            if c.fetchone():
                erro = "Esse email ja ta cadastrado."
            else:
                c.execute("INSERT INTO clientes (nome, email, senha) VALUES (?, ?, ?)", (nome, email, senha))
                conn.commit()
                cliente_id = c.lastrowid
                conn.close()
                session["cliente_id"] = cliente_id
                session["cliente_nome"] = nome
                return redirect(url_for("minha_conta"))
            conn.close()
    return render_template("cadastro.html", erro=erro)

@app.route("/entrar", methods=["GET", "POST"])
def entrar_cliente():
    if cliente_logado():
        return redirect(url_for("minha_conta"))
    erro = None
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, nome FROM clientes WHERE email=? AND senha=?", (email, senha))
        cliente = c.fetchone()
        conn.close()
        if cliente:
            session["cliente_id"] = cliente[0]
            session["cliente_nome"] = cliente[1]
            return redirect(url_for("minha_conta"))
        else:
            erro = "Email ou senha incorretos."
    return render_template("entrar.html", erro=erro)

@app.route("/minha-conta")
def minha_conta():
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, nome, email, criado_em FROM clientes WHERE id=?", (session["cliente_id"],))
    cliente = c.fetchone()
    conn.close()
    if not cliente:
        session.pop("cliente_id", None)
        session.pop("cliente_nome", None)
        return redirect(url_for("entrar_cliente"))
    return render_template("minha_conta.html", cliente=cliente)

@app.route("/sair-cliente")
def sair_cliente():
    session.pop("cliente_id", None)
    session.pop("cliente_nome", None)
    return redirect(url_for("index"))

# ============================================
# CARRINHO DE COMPRAS
# ============================================
@app.route("/carrinho")
def ver_carrinho():
    carrinho = session.get("carrinho", {})
    itens = []
    total = 0
    if carrinho:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        for pid, qtd in carrinho.items():
            c.execute("SELECT id, nome, preco, imagem, loja_id FROM produtos WHERE id=?", (pid,))
            p = c.fetchone()
            if p:
                subtotal = p[2] * qtd
                total += subtotal
                itens.append({
                    "id": p[0], "nome": p[1], "preco": p[2],
                    "imagem": p[3], "loja_id": p[4],
                    "quantidade": qtd, "subtotal": subtotal
                })
        conn.close()
    return render_template("carrinho.html", itens=itens, total=total)

@app.route("/carrinho/adicionar/<int:produto_id>", methods=["POST"])
def adicionar_carrinho(produto_id):
    carrinho = session.get("carrinho", {})
    pid = str(produto_id)
    carrinho[pid] = carrinho.get(pid, 0) + 1
    session["carrinho"] = carrinho
    return redirect(request.referrer or url_for("index"))

@app.route("/carrinho/remover/<int:produto_id>", methods=["POST"])
def remover_carrinho(produto_id):
    carrinho = session.get("carrinho", {})
    pid = str(produto_id)
    if pid in carrinho:
        del carrinho[pid]
    session["carrinho"] = carrinho
    return redirect(url_for("ver_carrinho"))

@app.route("/carrinho/atualizar/<int:produto_id>/<acao>", methods=["POST"])
def atualizar_carrinho(produto_id, acao):
    carrinho = session.get("carrinho", {})
    pid = str(produto_id)
    if pid in carrinho:
        if acao == "mais":
            carrinho[pid] += 1
        elif acao == "menos":
            carrinho[pid] -= 1
            if carrinho[pid] <= 0:
                del carrinho[pid]
    session["carrinho"] = carrinho
    return redirect(url_for("ver_carrinho"))

@app.context_processor
def injetar_contexto():
    carrinho = session.get("carrinho", {})
    total_itens = sum(carrinho.values()) if carrinho else 0
    return {
        "total_carrinho": total_itens,
        "cliente_logado": session.get("cliente_id") is not None,
        "cliente_nome": session.get("cliente_nome", "")
    }


# ============================================
# SISTEMA DE PEDIDOS
# ============================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    carrinho = session.get("carrinho", {})
    if not carrinho:
        return redirect(url_for("ver_carrinho"))
    
    itens = []
    total = 0
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    for pid, qtd in carrinho.items():
        c.execute("SELECT id, nome, preco FROM produtos WHERE id=?", (pid,))
        p = c.fetchone()
        if p:
            subtotal = p[2] * qtd
            total += subtotal
            itens.append({"id": p[0], "nome": p[1], "preco": p[2], "quantidade": qtd, "subtotal": subtotal})
    
    # Só processa POST DE VERDADE (com o campo nome_entrega)
    if request.method == "POST" and "nome_entrega" in request.form:
        nome_entrega = request.form["nome_entrega"].strip()
        endereco = request.form["endereco"].strip()
        cidade = request.form["cidade"].strip()
        cep = request.form["cep"].strip()
        
        if all([nome_entrega, endereco, cidade, cep]):
            c.execute("INSERT INTO pedidos (cliente_id, nome_entrega, endereco, cidade, cep, total, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (session["cliente_id"], nome_entrega, endereco, cidade, cep, total, "pendente"))
            pedido_id = c.lastrowid
            
            for item in itens:
                c.execute("INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, preco, quantidade) VALUES (?, ?, ?, ?, ?)",
                          (pedido_id, item["id"], item["nome"], item["preco"], item["quantidade"]))
            
            conn.commit()
            conn.close()
            session["carrinho"] = {}
            return redirect(url_for("ver_pedido", pedido_id=pedido_id))
    
    conn.close()
    return render_template("checkout.html", itens=itens, total=total)

@app.route("/pedido/<int:pedido_id>")
def ver_pedido(pedido_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, cliente_id, nome_entrega, endereco, cidade, cep, total, status, criado_em FROM pedidos WHERE id=? AND cliente_id=?",
              (pedido_id, session["cliente_id"]))
    pedido = c.fetchone()
    
    if not pedido:
        conn.close()
        return render_template("404.html"), 404
    
    c.execute("SELECT nome_produto, preco, quantidade FROM itens_pedido WHERE pedido_id=?", (pedido_id,))
    itens = c.fetchall()
    conn.close()
    
    return render_template("pedido_confirmado.html", pedido=pedido, itens=itens)

@app.route("/meus-pedidos")
def meus_pedidos():
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, total, status, criado_em FROM pedidos WHERE cliente_id=? ORDER BY id DESC",
              (session["cliente_id"],))
    pedidos = c.fetchall()
    conn.close()
    
    return render_template("meus_pedidos.html", pedidos=pedidos)


# ============================================
# PAINEL DO ADM - PEDIDOS
# ============================================

@app.route("/admin/pedidos")
def admin_pedidos():
    if "adm" not in session:
        return redirect(url_for("login"))
    
    filtro = request.args.get("status", "").strip()
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    if filtro:
        c.execute("""
            SELECT p.id, p.total, p.status, p.criado_em, p.nome_entrega, c.nome
            FROM pedidos p
            JOIN clientes c ON c.id = p.cliente_id
            WHERE p.status = ?
            ORDER BY p.id DESC
        """, (filtro,))
    else:
        c.execute("""
            SELECT p.id, p.total, p.status, p.criado_em, p.nome_entrega, c.nome
            FROM pedidos p
            JOIN clientes c ON c.id = p.cliente_id
            ORDER BY p.id DESC
        """)
    pedidos = c.fetchall()
    
    # Estatísticas
    c.execute("SELECT COUNT(*) FROM pedidos")
    total_pedidos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pedidos WHERE status='pendente'")
    pendentes = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(total), 0) FROM pedidos WHERE status != 'cancelado'")
    total_vendas = c.fetchone()[0]
    
    conn.close()
    
    return render_template("admin_pedidos.html",
                           pedidos=pedidos,
                           filtro=filtro,
                           total_pedidos=total_pedidos,
                           pendentes=pendentes,
                           total_vendas=total_vendas)

@app.route("/admin/pedido/<int:pedido_id>")
def admin_ver_pedido(pedido_id):
    if "adm" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.cliente_id, p.nome_entrega, p.endereco, p.cidade, p.cep,
               p.total, p.status, p.criado_em, cl.nome, cl.email
        FROM pedidos p
        JOIN clientes cl ON cl.id = p.cliente_id
        WHERE p.id = ?
    """, (pedido_id,))
    pedido = c.fetchone()
    
    if not pedido:
        conn.close()
        return render_template("404.html"), 404
    
    c.execute("SELECT nome_produto, preco, quantidade FROM itens_pedido WHERE pedido_id=?", (pedido_id,))
    itens = c.fetchall()
    conn.close()
    
    return render_template("admin_pedido_detalhe.html", pedido=pedido, itens=itens)

@app.route("/admin/pedido/<int:pedido_id>/status/<novo_status>", methods=["POST"])
def admin_mudar_status(pedido_id, novo_status):
    if "adm" not in session:
        return redirect(url_for("login"))
    
    if novo_status not in ["pendente", "enviado", "entregue", "cancelado"]:
        return "Status inválido", 400
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE pedidos SET status=? WHERE id=?", (novo_status, pedido_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for("admin_ver_pedido", pedido_id=pedido_id))


# ============================================
# CATEGORIAS
# ============================================

@app.route("/admin/categorias")
def admin_categorias():
    if "adm" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT cat.id, cat.nome, cat.icone, COUNT(l.id) as total_lojas
        FROM categorias cat
        LEFT JOIN lojas l ON l.categoria_id = cat.id
        GROUP BY cat.id
        ORDER BY cat.nome
    """)
    categorias = c.fetchall()
    conn.close()
    
    return render_template("admin_categorias.html", categorias=categorias)

@app.route("/admin/categorias/nova", methods=["POST"])
def admin_nova_categoria():
    if "adm" not in session:
        return redirect(url_for("login"))
    
    nome = request.form["nome"].strip()
    icone = request.form.get("icone", "X").strip() or "X"
    
    if nome:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO categorias (nome, icone) VALUES (?, ?)", (nome, icone))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    
    return redirect(url_for("admin_categorias"))

@app.route("/admin/categorias/<int:cat_id>/deletar", methods=["POST"])
def admin_deletar_categoria(cat_id):
    if "adm" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE lojas SET categoria_id = NULL WHERE categoria_id = ?", (cat_id,))
    c.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("admin_categorias"))


# ============================================
# AVALIACOES
# ============================================

@app.route("/produto/<int:produto_id>/avaliar", methods=["POST"])
def avaliar_produto(produto_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    nota = int(request.form.get("nota", 0))
    comentario = request.form.get("comentario", "").strip()
    
    if nota < 1 or nota > 5:
        return redirect(url_for("ver_produto", produto_id=produto_id))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id FROM avaliacoes WHERE produto_id=? AND cliente_id=?",
              (produto_id, session["cliente_id"]))
    existente = c.fetchone()
    
    if existente:
        c.execute("UPDATE avaliacoes SET nota=?, comentario=?, criado_em=CURRENT_TIMESTAMP WHERE id=?",
                  (nota, comentario, existente[0]))
    else:
        c.execute("INSERT INTO avaliacoes (produto_id, cliente_id, nota, comentario) VALUES (?, ?, ?, ?)",
                  (produto_id, session["cliente_id"], nota, comentario))
    
    conn.commit()
    conn.close()
    return redirect(url_for("ver_produto", produto_id=produto_id))


# ============================================
# PIX - PAGAMENTO
# ============================================
import qrcode
import io
import base64

def get_config(chave):
    """Pega um valor da tabela config."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE chave=?", (chave,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def gerar_string_pix(chave, nome, cidade, valor, txid="***"):
    """Gera a string EMV do Pix (padrão dos bancos)."""
    def tlv(id_, value):
        return f"{id_}{len(value):02d}{value}"
    
    valor_str = f"{valor:.2f}"
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()
    
    payload = (
        tlv("00", "01") +
        tlv("26", tlv("00", "BR.GOV.BCB.PIX") + tlv("01", chave)) +
        tlv("52", "0000") +
        tlv("53", "986") +
        tlv("54", valor_str) +
        tlv("58", "BR") +
        tlv("59", nome) +
        tlv("60", cidade) +
        tlv("62", tlv("05", txid))
    )
    
    crc = 0xFFFF
    for byte in (payload + "6304").encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    crc_hex = f"{crc:04X}"
    
    return payload + "6304" + crc_hex

def gerar_qr_base64(texto):
    """Gera QR code como imagem base64 pra embedar em HTML."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@app.route("/pedido/<int:pedido_id>/pagar")
def pagar_pedido(pedido_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, total, status FROM pedidos WHERE id=? AND cliente_id=?",
              (pedido_id, session["cliente_id"]))
    pedido = c.fetchone()
    conn.close()
    
    if not pedido:
        return render_template("404.html"), 404
    
    if pedido[2] == "pago":
        return redirect(url_for("ver_pedido", pedido_id=pedido_id))
    
    chave = get_config("pix_chave") or "chave@exemplo.com"
    nome = get_config("pix_nome") or "Recebedor"
    cidade = get_config("pix_cidade") or "CIDADE"
    
    string_pix = gerar_string_pix(chave, nome, cidade, pedido[1], f"PEDIDO{pedido_id}")
    qr_base64 = gerar_qr_base64(string_pix)
    
    return render_template("pagamento.html", pedido=pedido, string_pix=string_pix, qr_base64=qr_base64)

@app.route("/pedido/<int:pedido_id>/confirmar-pagamento", methods=["POST"])
def confirmar_pagamento(pedido_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE pedidos SET status='pago' WHERE id=? AND cliente_id=?",
              (pedido_id, session["cliente_id"]))
    conn.commit()
    conn.close()
    
    return redirect(url_for("ver_pedido", pedido_id=pedido_id))

@app.route("/admin/config", methods=["GET", "POST"])
def admin_config():
    if "adm" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        chave = request.form.get("pix_chave", "").strip()
        nome = request.form.get("pix_nome", "").strip()
        cidade = request.form.get("pix_cidade", "").strip()
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_chave', ?)", (chave,))
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_nome', ?)", (nome,))
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_cidade', ?)", (cidade,))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_config"))
    
    return render_template("admin_config.html",
                           pix_chave=get_config("pix_chave") or "",
                           pix_nome=get_config("pix_nome") or "",
                           pix_cidade=get_config("pix_cidade") or "")


# ============================================
# PIX - PAGAMENTO
# ============================================
import qrcode
import io
import base64

def get_config(chave):
    """Pega um valor da tabela config."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT valor FROM config WHERE chave=?", (chave,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def gerar_string_pix(chave, nome, cidade, valor, txid="***"):
    """Gera a string EMV do Pix (padrão dos bancos)."""
    def tlv(id_, value):
        return f"{id_}{len(value):02d}{value}"
    
    valor_str = f"{valor:.2f}"
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()
    
    payload = (
        tlv("00", "01") +
        tlv("26", tlv("00", "BR.GOV.BCB.PIX") + tlv("01", chave)) +
        tlv("52", "0000") +
        tlv("53", "986") +
        tlv("54", valor_str) +
        tlv("58", "BR") +
        tlv("59", nome) +
        tlv("60", cidade) +
        tlv("62", tlv("05", txid))
    )
    
    crc = 0xFFFF
    for byte in (payload + "6304").encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    crc_hex = f"{crc:04X}"
    
    return payload + "6304" + crc_hex

def gerar_qr_base64(texto):
    """Gera QR code como imagem base64 pra embedar em HTML."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@app.route("/pedido/<int:pedido_id>/pagar")
def pagar_pedido(pedido_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, total, status FROM pedidos WHERE id=? AND cliente_id=?",
              (pedido_id, session["cliente_id"]))
    pedido = c.fetchone()
    conn.close()
    
    if not pedido:
        return render_template("404.html"), 404
    
    if pedido[2] == "pago":
        return redirect(url_for("ver_pedido", pedido_id=pedido_id))
    
    chave = get_config("pix_chave") or "chave@exemplo.com"
    nome = get_config("pix_nome") or "Recebedor"
    cidade = get_config("pix_cidade") or "CIDADE"
    
    string_pix = gerar_string_pix(chave, nome, cidade, pedido[1], f"PEDIDO{pedido_id}")
    qr_base64 = gerar_qr_base64(string_pix)
    
    return render_template("pagamento.html", pedido=pedido, string_pix=string_pix, qr_base64=qr_base64)

@app.route("/pedido/<int:pedido_id>/confirmar-pagamento", methods=["POST"])
def confirmar_pagamento(pedido_id):
    if not cliente_logado():
        return redirect(url_for("entrar_cliente"))
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE pedidos SET status='pago' WHERE id=? AND cliente_id=?",
              (pedido_id, session["cliente_id"]))
    conn.commit()
    conn.close()
    
    return redirect(url_for("ver_pedido", pedido_id=pedido_id))

@app.route("/admin/config", methods=["GET", "POST"])
def admin_config():
    if "adm" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        chave = request.form.get("pix_chave", "").strip()
        nome = request.form.get("pix_nome", "").strip()
        cidade = request.form.get("pix_cidade", "").strip()
        
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_chave', ?)", (chave,))
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_nome', ?)", (nome,))
        c.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('pix_cidade', ?)", (cidade,))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_config"))
    
    return render_template("admin_config.html",
                           pix_chave=get_config("pix_chave") or "",
                           pix_nome=get_config("pix_nome") or "",
                           pix_cidade=get_config("pix_cidade") or "")

@app.route("/logout")
def logout():
    session.pop("adm", None)
    return redirect(url_for("index"))

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template("404.html"), 404

# Inicializa o banco
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
