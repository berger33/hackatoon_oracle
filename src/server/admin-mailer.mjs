// Fatia 07 — transporte REAL da fila administrativa de e-mails.
//
// Contexto medido (N7): `server.mjs` criava a API da fila com `mailer: null` e
// nenhum caminho ligava `MAIL_*` a ela. Configurar `MAIL_HOST` não conectava
// nada: toda notificação de e-mail caía na caixa local (`local_outbox`, que
// nunca significa envio) e, quando a caixa não estava disponível, acumulava
// tentativas até `dead`. Este módulo é a ligação que faltava — e só ela.
//
// Contrato preservado, lado a lado com o que já existia:
//
//   * a fila (`notification-queue.mjs`) continua sendo a dona do estado:
//     `queued → sending → sent | failed → dead`, com backoff e reivindicação
//     atômica. Nada disso muda aqui;
//   * sem configuração válida (`MAIL_HOST`/`MAIL_FROM`), o transporte NÃO é
//     criado e o chamador recebe `null`. A fila então mantém o comportamento
//     vigente: caixa local quando disponível, `not_configured` caso contrário.
//     Configuração parcial/inválida nunca vira "envio" — é fail-closed;
//   * o e-mail de LEAD (`sendLeadEmail` em `server.mjs`) e os avisos de
//     autenticação do cliente continuam intocados, com seu próprio caminho;
//   * nenhum destinatário é inventado: o endereço é o que a linha da fila já
//     tem em `recipient_email`.
//
// Garantias que este arquivo assume para não mentir sobre entrega:
//   * só devolve `sent` quando o provedor aceitou a mensagem (`sendMail`
//     resolveu com `accepted` contendo o destinatário). Resposta sem
//     `accepted`, vazia ou recusada vira erro, e a fila trata como falha;
//   * a mensagem enviada é marcada com `X-Seg-Notification-Id`, para que o
//     operador consiga correlacionar a caixa de saída do provedor com a fila.
//     A deduplicação em si continua sendo a da fila (chave única do banco);
//     este cabeçalho é rastro, não trava;
//   * nenhum log imprime usuário, senha, corpo da mensagem ou token.
//
// Limite declarado: isto é o transporte e sua configuração. Não é prova de
// recebimento no provedor do cliente final — isso exige domínio, remetente
// autorizado e verificação de entrega fora deste repositório.

import nodemailer from "nodemailer";

/** Estados que o chamador recebe ao validar a configuração. */
export const MAILER_STATE = Object.freeze({
  READY: "ready",
  NOT_CONFIGURED: "not_configured",
  INVALID: "invalid",
});

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_ADDRESS = 320;

/** Porta SMTP utilizável: inteiro 1..65535. Padrão 587 (submissão). */
function parsePort(raw) {
  if (raw === undefined || raw === null || String(raw).trim() === "") {
    return { value: 587, error: null };
  }
  const text = String(raw).trim();
  const value = Number(text);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    return { value: null, error: "invalid_mail_port" };
  }
  return { value, error: null };
}

/**
 * Lê e valida a configuração SMTP a partir do ambiente.
 *
 * Devolve `{ state, config, problems }`. `config` só existe em `ready`.
 * `problems` são códigos estáveis (sem echo de valores) para diagnóstico:
 *   invalid_mail_port · invalid_mail_secure · invalid_mail_from ·
 *   invalid_mail_host · invalid_mail_user · missing_mail_password ·
 *   orphan_mail_password · incomplete_mail_configuration
 *
 * Regras (as mesmas que o caminho de lead já pratica, agora explícitas):
 *   * `MAIL_HOST` e `MAIL_FROM` são obrigatórios para existir transporte;
 *   * `MAIL_SECURE` aceita true/false/1/0 sim/não; qualquer outro valor é
 *     inválido — não se adivinha TLS;
 *   * usuário e senha andam juntos (um sem o outro é configuração inválida,
 *     não autenticação anônima silenciosa);
 *   * `MAIL_FROM` precisa ser endereço plausível; o remetente não pode ser
 *     inventado pelo código.
 */
export function readMailTransportConfig(env = process.env) {
  const host = String(env.MAIL_HOST ?? "").trim();
  const from = String(env.MAIL_FROM ?? "").trim();
  const user = String(env.MAIL_USER ?? "").trim();
  const password = String(env.MAIL_PASSWORD ?? "");
  const secureRaw = String(env.MAIL_SECURE ?? "").trim().toLowerCase();

  const port = parsePort(env.MAIL_PORT);
  const problems = [];

  let secure = false;
  if (secureRaw === "" || secureRaw === "false" || secureRaw === "0" || secureRaw === "nao" || secureRaw === "não") {
    secure = false;
  } else if (secureRaw === "true" || secureRaw === "1" || secureRaw === "sim") {
    secure = true;
  } else {
    problems.push("invalid_mail_secure");
  }

  if (port.error) problems.push(port.error);

  const hasHost = host.length > 0;
  const hasFrom = from.length > 0;

  // Sem host e sem remetente não há configuração: estado declarado, não erro.
  // É o caso de toda instalação que não usa SMTP — e o comportamento vigente.
  if (!hasHost && !hasFrom) {
    return { state: MAILER_STATE.NOT_CONFIGURED, config: null, problems: [] };
  }

  if (hasHost && from && (from.length > MAX_ADDRESS || !EMAIL_PATTERN.test(from))) {
    problems.push("invalid_mail_from");
  }
  if (hasFrom && host && (host.length > 255 || /\s/.test(host))) {
    problems.push("invalid_mail_host");
  }
  if (user && user.length > MAX_ADDRESS) problems.push("invalid_mail_user");
  if (user && !password) problems.push("missing_mail_password");
  if (!user && password) problems.push("orphan_mail_password");

  // Configuração pela metade é ambígua: não se escolhe remetente/host por conta
  // própria. Qualquer metade preenchida sem a outra é inválida.
  if (hasHost !== hasFrom) problems.push("incomplete_mail_configuration");

  if (problems.length > 0) {
    return {
      state: MAILER_STATE.INVALID,
      config: null,
      problems: [...new Set(problems)].sort(),
    };
  }

  return {
    state: MAILER_STATE.READY,
    config: Object.freeze({
      host,
      port: port.value,
      // TLS implícito quando pedido explicitamente ou na porta 465 — mesma
      // regra do caminho de lead, para não existirem dois contratos.
      secure: secure || port.value === 465,
      user: user || null,
      password: password || null,
      from,
    }),
    problems: [],
  };
}

function extractMessageId(result) {
  if (!result || typeof result !== "object") return null;
  const value = result.messageId ?? result.message_id ?? null;
  return typeof value === "string" && value.length > 0 && value.length <= 998 ? value : null;
}

function acceptedCount(result, recipient) {
  const accepted = Array.isArray(result?.accepted) ? result.accepted : null;
  if (!accepted) return null;
  const target = String(recipient).trim().toLowerCase();
  return accepted.some((entry) => String(entry).trim().toLowerCase() === target) ? 1 : 0;
}

/** Mensagem legível para a coluna `last_error` (curta, sem segredo). */
function safeError(error) {
  if (!error) return "send_failed";
  const code = typeof error.code === "string" && /^[EW]_?[A-Z0-9]+$/i.test(error.code) ? `${error.code}: ` : "";
  const message = typeof error.message === "string" ? error.message : String(error);
  return `${code}${message}`.replace(/\s+/g, " ").slice(0, 500) || "send_failed";
}

/**
 * Constrói o transporte. Aceita `createTransport` injetado para que o teste
 * local use um SMTP de captura sem tocar no nodemailer real — mas o padrão é o
 * nodemailer, que é o contrato existente deste repositório.
 *
 * Devolve `null` quando a configuração não permite envio (ausente ou
 * inválida). Isso é intencional: `null` é exatamente o valor que a fila já
 * entende como "não configurado", e é melhor um `null` explícito do que um
 * transporte que falha no primeiro item e enfileira retentativas inúteis.
 */
export function createAdminMailTransport({ env = process.env, createTransport, logger = console } = {}) {
  const read = readMailTransportConfig(env);
  if (read.state !== MAILER_STATE.READY) {
    if (read.state === MAILER_STATE.INVALID) {
      // Diagnóstico sem valor sensível: só os códigos. Assim o operador sabe
      // que configurou e a configuração foi recusada, em vez de achar que
      // "não configurou".
      logger.error("admin mail transport refused: invalid configuration", { problems: read.problems });
    }
    return null;
  }

  // `createTransport` é injetável para o teste local; o padrão é o nodemailer
  // que este repositório já usa (import estático, como em `server.mjs`).
  const factory = createTransport || ((options) => nodemailer.createTransport(options));
  const transporter = factory({
    host: read.config.host,
    port: read.config.port,
    secure: read.config.secure,
    auth: read.config.user ? { user: read.config.user, pass: read.config.password } : undefined,
    connectionTimeout: 8_000,
    greetingTimeout: 8_000,
    socketTimeout: 12_000,
  });

  /**
   * Envia UMA linha da fila de notificações e devolve `"sent"` ou lança erro.
   *
   * Lançar (e não devolver um estado ambíguo) é deliberado: o contrato de
   * `notification-queue.processNext` traduz exceção em `failed` + backoff e,
   * após `max_attempts`, `dead`. Um retorno tipo "talvez" registraria a
   * mensagem como enviada sem prova.
   */
  async function sendNotification(row) {
    if (!row || typeof row !== "object") throw new Error("invalid_notification_row");
    const recipient = typeof row.recipient_email === "string" ? row.recipient_email.trim() : "";
    if (!recipient || recipient.length > MAX_ADDRESS || !EMAIL_PATTERN.test(recipient)) {
      // Erro definitivo: sem destinatário válido não há o que regerar.
      const error = new Error("invalid_recipient_email_for_delivery");
      error.code = "EINVALIDRECIPIENT";
      throw error;
    }

    const template = String(row.template || "notificacao").slice(0, 100);
    const subject = `[${template}] Notificação Grupo SEG`;
    const text = [
      `Notificação ${template}`,
      "",
      "Conteúdo registrado pela fila administrativa:",
      JSON.stringify(row.payload ?? {}, null, 2),
      "",
      "Referência da fila: " + String(row.id || "(sem id)"),
      "",
      "Esta mensagem foi produzida pelo sistema Grupo SEG a partir da fila",
      "administrativa. Ela não contém dados de clientes além do conteúdo",
      "registrado pelo operador que a criou.",
    ].join("\n");

    let result;
    try {
      result = await transporter.sendMail({
        from: read.config.from,
        to: recipient,
        subject,
        text,
        headers: row.id ? { "X-SEG-Notification-Id": String(row.id) } : undefined,
      });
    } catch (error) {
      // Reembrulha com mensagem curta e código preservado; nada de segredo.
      const wrapped = new Error(safeError(error));
      wrapped.code = typeof error?.code === "string" ? error.code : "ESENDMAIL";
      throw wrapped;
    }

    // Sem prova de aceite não se declara envio.
    const accepted = acceptedCount(result, recipient);
    if (accepted === 0) {
      const rejected = Array.isArray(result?.rejected) ? result.rejected.join(",") : "";
      const error = new Error(`recipient_not_accepted${rejected ? `: ${rejected}` : ""}`);
      error.code = "ERECIPIENTREJECTED";
      throw error;
    }
    if (accepted === null && !extractMessageId(result)) {
      const error = new Error("sendmail_without_acceptance_evidence");
      error.code = "ENOACCEPTANCE";
      throw error;
    }

    return "sent";
  }

  // O contrato que a fila entende melhor é o de FUNÇÃO (`typeof mailer ===
  // "function"` → `await mailer(row)`): é o único em que a montagem da
  // mensagem passa por este módulo, com remetente configurado e prova de
  // aceite. O caminho `mailer.sendMail({...})` da fila não informa `from`, e
  // sem remetente o envelope sai vazio (`MAIL FROM:<>`) — por isso `sendMail`
  // também injeta o remetente configurado quando o chamador não informa um.
  async function mailer(row) {
    return sendNotification(row);
  }

  mailer.transport = "smtp";
  mailer.state = MAILER_STATE.READY;
  mailer.sendNotification = sendNotification;
  mailer.describe = () => ({
    transport: "smtp",
    host: read.config.host,
    port: read.config.port,
    secure: read.config.secure,
    authenticated: Boolean(read.config.user),
    from: read.config.from,
  });
  mailer.sendMail = (options = {}) => transporter.sendMail({
    ...options,
    from: options.from || read.config.from,
  });
  mailer.close = () => (typeof transporter.close === "function" ? transporter.close() : undefined);

  return mailer;
}

/**
 * Conveniência para `server.mjs`: mantém a dependência injetável (o teste usa
 * SMTP de captura) sem carregar o nodemailer duas vezes.
 */
export function createAdminMailer({ env = process.env, createTransport, logger = console } = {}) {
  return createAdminMailTransport({ env, createTransport, logger });
}

/**
 * Descreve o estado para a tela/consumidores, sem expor configuração sensível.
 * `not_configured` e `invalid` são estados de primeira classe: a fila precisa
 * poder declarar por que não envia.
 */
export function describeAdminMailerState(env = process.env) {
  const read = readMailTransportConfig(env);
  if (read.state === MAILER_STATE.READY) {
    return {
      state: MAILER_STATE.READY,
      host: read.config.host,
      port: read.config.port,
      secure: read.config.secure,
      authenticated: Boolean(read.config.user),
    };
  }
  return { state: read.state, problems: read.problems };
}
