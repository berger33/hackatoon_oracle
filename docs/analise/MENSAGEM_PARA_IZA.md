# Mensagem para a Iza — versão final (revisada após a fala do Cris)

> Pronta para colar no Discord. Baseada na verificação do repositório oficial
> (`develop` e `feature/oci-historico-json`) e na mensagem do Cris de 22:33.

---

Oi, Iza, tudo bem?

Terminei a revisão dos três PRs (#21, #22 e #23) e do pacote de evidências. Não li por cima: clonei o repositório oficial, rodei a suíte nas suas branches, executei os casos do catálogo contra a API de verdade e validei os `expected.json` no contrato. Começo pelo que importa: **o seu trabalho está correto, bem feito e não precisa ser refeito**. As ressalvas abaixo são de fechamento.

## O que eu confirmei

Reproduzi **298 passed / 1 skipped** na `develop` (PR #21) e **306 passed / 1 skipped** na sua branch (PR #22). O skip é o `test_adapter_nao_descarta_campos_novos_no_contrato_legado`, protegido por `skipif(NOVO_CONTRATO)` — é intencional, não dívida.

O adaptador do envelope preserva `urgencia`, `campos_incertos` e `conflitos` sem duplicar regra do grafo. Sobre o limiar, o Cris já trouxe a confirmação na camada dele e eu confirmei a mesma coisa: vem sempre da aplicação (`os.getenv("LIMIAR_CONFIANCA", "0.85")`), o grafo compara deterministicamente em `graph.py:262` e registra o valor aplicado em `limiar_aplicado`. Sondei o envelope mandando um `limiar` dentro dele: a chave é ignorada, o valor da aplicação prevalece. Um detalhe que reforça a mesma regra — e que **não** é problema do seu PR: se alguém revalidar o payload final com um `limiar_aplicado` diferente do configurado, o validador de contrato obedece ao payload, não à configuração. Testei com 0.10 sobre o caso `Borda_Score_084` e um score de 0.84 saiu `PROCESSADO`. É furo meu para fechar, não seu.

No histórico, testei o ciclo completo com conector falso: snapshot imutável com nome único, referência só depois da confirmação, falha só do histórico gerando `ERRO_PERSISTENCIA` sem perder original nem resultado, e a retentativa gravando só o histórico. Funciona como você descreveu.

## Suas perguntas, respondidas

**`LIMIAR_CONFIANCA` com padrão 0.85:** confirmado como configuração oficial do MVP. É decisão fechada. Só falta colocar a variável no `.env.example` e no README, porque ela é usada em quatro pontos do código e não está documentada ainda — vou falar com a Luciana e trabalhar nisso nos próximos dias.

**Regra de conflitos repetidos:** está de acordo. É o que o grafo faz: tipo normalizado + gravidade + conjunto de campos + descrição contam uma vez; descrição diferente continua conflito distinto. Tem teste dedicado.

**Cenários de referência:** os **79 fixtures** (`tests/fixtures/` + `manifest.csv`). **Não** os `cenario_1..3_*.json` — eles ainda usam rótulos antigos e o cenário 3 declara dois destinos (`Fila_Revisao_Humana` + `Farmacia_Hospitalar`), que o contrato atual não produz. Se alguém implementar em cima daquele JSON, implementa algo que o sistema não gera.

## A decisão de urgência: fechada, e no sentido que já está implementado

Você está certa em não registrar o aceite ainda, e agora eu tenho a decisão. Olhando só o repositório oficial, o contrato, o código e os fixtures **já concordam entre si** em `PROCESSADO` + `requer_auditoria_humana = false`: é o que diz a R1 do `CONTRATO_DE_DADOS.md`, é o que faz o `clinical.py:632` (`requer_auditoria_humana = ambiguidade`) e é o que os fixtures oficiais de urgência declaram.

E apareceu uma coisa importante nessa checagem, que **melhora o argumento**: a própria regra R2 do contrato define ambiguidade como *"campo obrigatório ausente ou campo incerto ou conflito impeditivo ou score abaixo do limiar ou tipo fora da taxonomia ou prioridade `NAO_IDENTIFICADA` ou urgência `INDETERMINADO`"* — **urgência não está na lista**. E o RF-21 da E.F., que é o requisito que define revisão humana, lista exatamente os mesmos gatilhos: *"ambiguidade, ilegibilidade, conflito impeditivo, score combinado abaixo do limiar ou ausência de qualquer campo obrigatório"* — também sem urgência. Ou seja: os dois artefatos que definem **quando** há revisão concordam entre si. O que divergiu foi a **tabela** da §8.2, que escreveu "revisão obrigatória" na linha de urgência isolada.

Minha posição, então: **mantém como está** — urgência isolada termina em `PROCESSADO` com `requer_auditoria_humana = false`, um único destino (`FILA_URGENCIA_MEDICA`) e o alerta registrado. A auditoria da urgência acontece na própria fila urgente, que é para onde o alerta chama o plantão; `requer_auditoria_humana = false` não significa "ninguém vai olhar", significa que não precisa do fluxo de revisão/correção antes de liberar. Qualquer ambiguidade junto — a lista fechada acima — continua levando a `EM_REVISAO` com as duas filas, sem exceção. São 5 dos 8 fixtures urgentes afetados; os outros 3 (`Conflito_Prioridade`, `Simultaneo_Urgencia_Ilegivel`, `Simultaneo_Urgencia_Score`) já estão corretos e não mudam.

O que sobra para mim é reconciliar a linha da §8.2 com a R2 e o RF-21, e ajustar a seção "a exceção da urgência, explicada" no contrato, que hoje só existe para justificar a si mesma. Se você discordar, me fala até amanhã, mas já vou registrar assim. **Do seu lado não muda nada: você já está coerente com isso.**

## Dois pedidos no PR #22

**O primeiro é bloqueante.** Você escreveu que não comprovou a conversão de falha de análise em resultado de erro — eu fui ver e **não existe mesmo**. Injetei falha no grafo: `POST` devolve 202, o `GET` devolve `500 ERRO_INTERNO`, o status interno fica travado em `PROCESSANDO` e o histórico registra `RECEBIDO, PROCESSANDO, PROCESSANDO`.

Isso fere dois pontos da EF, e vale citar os dois no cartão:

- **RNF-03 (Confiabilidade):** *"Falha não deve perder documento. Simular indisponibilidade de Gemini/OCI; status e retry devem ser observáveis."* Hoje o status não é observável — ele mente, fica em `PROCESSANDO` para sempre.
- **Critério de aceite 6:** *"Submissão da API retorna 202 com ID e consulta posterior mostra estados e resultado final."* Um `ERRO_INTERNO` com 500 não é estado final nenhum.

Envolve a extração e o grafo em `try/except` e persiste `ERRO_PROCESSAMENTO` com `erro={codigo, mensagem}`, evento no histórico e sem travar o status. É o item que ficou aberto.

**O segundo:** reenvio do mesmo `documento_id` fica preso. O conector manda `if_none_match="*"`, e você já confere os bytes no 412 do **original** — mas não faz o mesmo no **resultado** nem no snapshot de histórico. Testei: primeiro envio em `EM_REVISAO` com tudo gravado, segundo envio do mesmo id cai em `ERRO_PERSISTENCIA`, e o `reprocessar-persistencia` devolve 502 porque o resultado também já existe. Documento íntegro sem saída. Replica a conferência nos três objetos e adiciona um teste com dois envios do mesmo id.

**Sobre a prova no OCI real:** o script está muito bom. Só vale ser específica no cartão 09 — como a API ainda extrai por heurística e o bucket recebe texto, o que foi provado é que o conector grava e lê original, resultado e snapshot, não que os três cenários clínicos funcionam ponta a ponta. E o relatório cai em `temp/`, que está no `.gitignore`; as capturas estão no PR, o JSON não. Se a banca pedir a prova, ela precisa existir fora da sua máquina.

## No catálogo, o único furo real

Não existe nenhum teste que abra a fixture `Validacao_ArquivoZip.zip` — nenhum. DOCX e EXE têm cobertura, ZIP não. Falta também um teste da conversão `ARQUIVO_VAZIO` / `CONTEUDO_TXT_VAZIO` da ingestão para `CAMPOS_INVALIDOS` na API.

**Sobre o PDF corrompido:** as duas coisas estão certas, em etapas diferentes. HTTP 422 com `PDF_CORROMPIDO` é rejeição de requisição, não vira triagem. `ERRO_PROCESSAMENTO` é documento aceito que falhou na leitura. Como o loader abre o PDF na submissão, hoje o 422 vem primeiro. Escreve assim no catálogo: no MVP a falha de abertura é capturada na borda, e o `ERRO_PROCESSAMENTO` fica reservado para falha depois do aceite — que é justamente o que falta implementar no item acima. Aí os dois documentos param de se contradizer.

**CLA-07:** enquadra pedido de exames em `GUIA_PROCEDIMENTO` e relatório cirúrgico em `RELATORIO_ALTA_INTERNACAO`. **CLA-08:** `OUTRO` é documento legível fora da taxonomia, `NAO_IDENTIFICADO` é quando o sistema não conseguiu determinar o tipo — nota fiscal pode ficar em `OUTRO`, não precisa de fixture nova. **CLA-09:** ilegibilidade está coberta, híbrido não. Sugiro uma fixture `Conflito_Hibrido` (receita + laudo no mesmo PDF) exigindo revisão. É simples e fecha a lacuna.

## Um aviso sobre o Anexo A (corrigindo o que eu disse antes)

Fui conferir no código oficial e o resultado é melhor do que eu tinha dito: **A1, A4 e A5 estão implementados** em `src/schemas/clinical.py` (linhas 220 e 603–609). Conflito `BAIXA` não bloqueia, prioridade `NAO_IDENTIFICADA` e urgência `INDETERMINADO` geram revisão. Está correto.

Sobra um ponto no **A3**: a fórmula está implementada de verdade dentro do `graph.py` (linhas 190–214, pesos 0.30 / 0.20 / 0.10 com piso em 0.0) — a **regra** existe. O que **não** existe são os artefatos nomeados que o Anexo A cita: `calcular_score_extracao` e `PESO_CONFLITO` não estão em `src/`, `tests/` nem `scripts/`. É correção de documentação ou extração da função para um módulo comum, porque hoje só o grafo tem a fórmula. Isso não afeta o seu PR — é item meu.

Duas observações para quem for mexer nesse Anexo: a numeração vai de **A1 direto para A3** (não existe A2), e o rótulo "A3" no contrato significa **cálculo do score**, não limiar — se essa sigla estiver circulando no Discord com outro sentido, vale alinhar antes de virar documento, porque a regra do limiar é a **R2**.

## Fechando

- **Streamlit + envelope (cartão 05):** aceite técnico OK, só registrando que o bloco de armazenamento é demonstrativo e que a API ainda não reproduz os sinais.
- **Confiança e sinais de revisão (cartão 06):** com a decisão acima publicada, é aceite. A implementação em si está correta.
- **Histórico no OCI (cartão 09):** aceite condicional aos dois ajustes.
- **Catálogo ING/CLA/EXT (seção 16):** aceite condicional, com as respostas desta mensagem incorporadas e ZIP e híbrido registrados como pendência explícita.

Vou registrar a decisão de urgência ainda hoje e te aviso aqui mesmo. Obrigado pelo cuidado de sempre separar o que foi validado do que ficou pendente — é isso que está deixando essa revisão fácil.

Abraço,
William

---

## Changelog desta versão

| Correção | Motivo |
| --- | --- |
| "testei se o limiar do envelope era ignorado, e é" | Mantida, mas agora explicitando que é a **chave do envelope** que é ignorada — a contradição com o Cris estava em sugerir que *qualquer* limiar de payload é ignorado. O furo do `limiar_aplicado` foi isolado numa frase própria e atribuído a mim, não ao PR dela. |
| Anexo A | Reformulado: A1/A4/A5 OK; o A3 **está implementado no `graph.py`**, faltam só os artefatos nomeados. Inclui a nota de que não existe A2 e de que "A3" ≠ limiar. |
| Urgência | Reforçada com a R2 do contrato e o RF-21 da EF, que listam os gatilhos de revisão sem incluir urgência. O conflito fica restrito à tabela da §8.2. |
| Removido | `docs/testes/CONTRATO_DE_DADOS.md` e `clinical.py` ficaram sem link markdown (o Discord embaralha), e "Decisão Arquitetural A3" não é citada como se existisse. |
| Cartões | Nomeados por assunto com o número entre parênteses, já que a numeração não está registrada em lugar nenhum do repositório. |
