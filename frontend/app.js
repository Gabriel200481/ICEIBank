// Model - acesso a API e ao estado persistido (localStorage)
const Sessao = {
  TOKEN_KEY: "iceibank_token",
  USUARIO_KEY: "iceibank_usuario",

  salvar(token, usuario) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USUARIO_KEY, usuario);
  },
  limpar() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USUARIO_KEY);
  },
  token() {
    return localStorage.getItem(this.TOKEN_KEY);
  },
  usuario() {
    return localStorage.getItem(this.USUARIO_KEY);
  },
};

const Api = {
  baseUrl() {
    return document.getElementById("baseUrl").value;
  },

  async chamar(caminho, opcoes = {}) {
    const resposta = await fetch(`${this.baseUrl()}${caminho}`, {
      ...opcoes,
      headers: {
        "Content-Type": "application/json",
        ...(Sessao.token() ? { Authorization: `Bearer ${Sessao.token()}` } : {}),
        ...(opcoes.headers || {}),
      },
    });

    let corpo = null;
    try {
      corpo = await resposta.json();
    } catch {
      corpo = null;
    }

    if (resposta.status === 401) {
      Sessao.limpar();
      Vista.mostrarLogin();
      const detalhe = corpo?.detail || "Sessao expirada.";
      throw new Error(`Sessao encerrada (${detalhe}). Faca login novamente.`);
    }

    if (!resposta.ok) {
      throw new Error(corpo?.detail || `Erro HTTP ${resposta.status}`);
    }

    return corpo;
  },
};

// View - manipulacao do DOM
const Vista = {
  mostrarMensagem(texto, tipo = "erro") {
    const elemento = document.getElementById("mensagem");
    elemento.textContent = texto;
    elemento.className = `mensagem ${tipo}`;
    elemento.hidden = false;
  },

  limparMensagem() {
    document.getElementById("mensagem").hidden = true;
  },

  mostrarApp(usuario) {
    document.getElementById("secao-login").hidden = true;
    document.getElementById("secao-app").hidden = false;
    document.getElementById("usuario-logado").textContent = usuario;
    document.getElementById("agencia-logada").textContent =
      document.getElementById("baseUrl").selectedOptions[0].textContent;
  },

  mostrarLogin() {
    document.getElementById("secao-login").hidden = false;
    document.getElementById("secao-app").hidden = true;
  },

  mostrarSaldo(conta) {
    document.getElementById("resultado-saldo").textContent =
      `Conta ${conta.id} (${conta.nomeAluno}): saldo R$ ${Number(conta.saldo).toFixed(2)}`;
  },
};

// Controller - liga eventos do DOM as chamadas de API
const Controlador = {
  async login(evento) {
    evento.preventDefault();
    Vista.limparMensagem();
    const usuario = document.getElementById("login-usuario").value;
    const senha = document.getElementById("login-senha").value;
    try {
      const dados = await Api.chamar("/auth/login", {
        method: "POST",
        body: JSON.stringify({ usuario, senha }),
      });
      Sessao.salvar(dados.access_token, usuario);
      Vista.mostrarMensagem("Login realizado com sucesso.", "sucesso");
      Vista.mostrarApp(usuario);
    } catch (erro) {
      Vista.mostrarMensagem(`Falha no login: ${erro.message}`);
    }
  },

  logout() {
    Sessao.limpar();
    Vista.mostrarLogin();
    Vista.limparMensagem();
  },

  async criarConta(evento) {
    evento.preventDefault();
    Vista.limparMensagem();
    const id = Number(document.getElementById("criar-id").value);
    const nomeAluno = document.getElementById("criar-nome").value;
    const saldoInicial = Number(document.getElementById("criar-saldo").value || 0);
    try {
      await Api.chamar("/contas", {
        method: "POST",
        body: JSON.stringify({ id, nomeAluno, saldoInicial }),
      });
      Vista.mostrarMensagem(`Conta ${id} criada com sucesso.`, "sucesso");
    } catch (erro) {
      Vista.mostrarMensagem(`Erro ao criar conta: ${erro.message}`);
    }
  },

  async consultarSaldo(evento) {
    evento.preventDefault();
    Vista.limparMensagem();
    const id = document.getElementById("saldo-id").value;
    try {
      const conta = await Api.chamar(`/contas/${id}`);
      Vista.mostrarSaldo(conta);
    } catch (erro) {
      document.getElementById("resultado-saldo").textContent = "";
      Vista.mostrarMensagem(`Erro ao consultar saldo: ${erro.message}`);
    }
  },

  async depositarOuSacar(evento) {
    evento.preventDefault();
    Vista.limparMensagem();
    const acao = evento.submitter?.dataset?.acao || "depositar";
    const id = document.getElementById("ds-id").value;
    const valor = Number(document.getElementById("ds-valor").value);
    try {
      const conta = await Api.chamar(`/contas/${id}/${acao}`, {
        method: "POST",
        body: JSON.stringify({ valor }),
      });
      const rotulo = acao === "depositar" ? "Deposito" : "Saque";
      Vista.mostrarMensagem(`${rotulo} concluido. Novo saldo: R$ ${Number(conta.saldo).toFixed(2)}`, "sucesso");
    } catch (erro) {
      Vista.mostrarMensagem(`Erro: ${erro.message}`);
    }
  },

  async transferir(evento) {
    evento.preventDefault();
    Vista.limparMensagem();
    const idOrigem = Number(document.getElementById("tr-origem").value);
    const idDestino = Number(document.getElementById("tr-destino").value);
    const valor = Number(document.getElementById("tr-valor").value);
    try {
      const resultado = await Api.chamar("/transferencias", {
        method: "POST",
        body: JSON.stringify({ idOrigem, idDestino, valor }),
      });
      Vista.mostrarMensagem(resultado.mensagem, "sucesso");
    } catch (erro) {
      Vista.mostrarMensagem(`Erro na transferencia: ${erro.message}`);
    }
  },
};

document.getElementById("form-login").addEventListener("submit", (e) => Controlador.login(e));
document.getElementById("botao-logout").addEventListener("click", () => Controlador.logout());
document.getElementById("form-criar-conta").addEventListener("submit", (e) => Controlador.criarConta(e));
document.getElementById("form-saldo").addEventListener("submit", (e) => Controlador.consultarSaldo(e));
document.getElementById("form-deposito-saque").addEventListener("submit", (e) => Controlador.depositarOuSacar(e));
document.getElementById("form-transferencia").addEventListener("submit", (e) => Controlador.transferir(e));

// Restaura a sessao se ja havia um token salvo de uma visita anterior.
if (Sessao.token()) {
  Vista.mostrarApp(Sessao.usuario() || "aluno");
}
