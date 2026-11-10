# Eventos do Campus

Sistema de inscrições em eventos do campus, desenvolvido em Django 4.2 na disciplina de
Rapid Application Development (RAD), Tecnólogo em Sistemas para Internet, IFPB.

- **Ponto Extra II:** o site HTML.
- **Atividade 06:** a API REST, ao lado do site e sobre os mesmos models ([seção da API](#api-rest)).
- **Atividade 08:** testes automatizados das duas camadas, com a tabela de sabotagem ([seção de testes](#testes-automatizados)).

Um evento reúne atividades (palestras, treinamentos e apresentações), cada uma numa sala e num horário.
O participante se inscreve no evento e, dentro dele, escolhe as atividades, respeitando a capacidade
da sala e sem conflitos de horário, mesmo entre eventos diferentes.

## Integrantes

- Suetone Carneiro

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

O `db.sqlite3` já vem com os dados de teste. Para recriá-los num banco vazio:

```bash
python manage.py popular_dados            # cria contas e dados (não duplica)
python manage.py popular_dados --limpar   # apaga salas/eventos/inscrições e recria
```

Testes automatizados (163 testes, cerca de 0,5 s; veja a [seção de testes](#testes-automatizados)):

```bash
python manage.py test
```

## Contas de teste

| # | Usuário | Senha         | Papel         | Para que serve                                        |
|---|---------|---------------|---------------|-------------------------------------------------------|
| 1 | `admin` | `admin`       | Superusuário  | Cadastrar salas pelo Admin (`/admin/`)                |
| 2 | `ana`   | `eventos2026` | Organizadora  | Organiza a Semana de Tecnologia e o Encontro de Egressos |
| 3 | `bruno` | `eventos2026` | Organizador   | Organiza a Jornada Científica; não altera nada da Ana |
| 4 | `carla` | `eventos2026` | Participante  | Inscrever-se                                          |
| 5 | `diego` | `eventos2026` | Participante  | Ocupar a última vaga do Laboratório 1                 |

Tokens da API (cabeçalho `Authorization: Token <chave>`):

| Usuário | Token |
|---------|-------|
| `admin` | `39e78f2a6f30acf8ddb4c3baa94f41c1c0260b91` |
| `ana` | `b419d7bd3ba08ac9e3ce2d7725249f0b48fcd0c7` |
| `bruno` | `c83b2c2c0456d817dc37f1b5a199e46474c541a9` |
| `carla` | `275a7a694f0e0d4f078a807f4eb3f0b662be327c` |
| `diego` | `0514e71483b5d588d3925380bc814c16ccd141d5` |

Os tokens são fixos (definidos no `popular_dados`), então continuam valendo se o banco for recriado.
Também é possível obter o token de qualquer conta com `POST /api/token/` (`username` e `password`).

Organizadores são os usuários do grupo **Organizadores** (criado automaticamente no `migrate`, com as
permissões de adicionar, alterar, excluir e ver eventos e atividades). Quem se cadastra pelo site entra
sem grupo, ou seja, como participante comum.

## Dados cadastrados

O banco foi entregue **sem inscrições**, para que os testes de inscrição comecem do zero.

### Salas

| Sala          | Bloco | Capacidade |
|---------------|-------|-----------:|
| Auditório     | A     | 100        |
| **Laboratório 1** | B | **2** ← sala pequena, para testar o limite de vagas |
| Sala 203      | C     | 30         |

### Eventos

| Evento               | Período            | Organizador | Inscrições |
|----------------------|--------------------|-------------|------------|
| Semana de Tecnologia | 10/11 a 14/11/2026 | ana         | abertas    |
| Jornada Científica   | 12/11 a 13/11/2026 | bruno       | abertas    |
| Encontro de Egressos | 05/12/2026         | ana         | **fechadas** |

A Semana e a Jornada têm **períodos que se cruzam** (12 e 13/11).

### Atividades

| Evento   | Atividade                      | Tipo         | Sala          | Dia   | Horário     |
|----------|--------------------------------|--------------|---------------|-------|-------------|
| Semana   | Abertura: o futuro da web      | Palestra     | Auditório     | 11/11 | 09:00–10:30 |
| Semana   | Oficina de Django              | Treinamento  | Laboratório 1 | 11/11 | 10:00–12:00 |
| Semana   | Git na prática                 | Treinamento  | Laboratório 1 | 11/11 | 14:00–16:00 |
| Semana   | Projetos dos alunos            | Apresentação | Sala 203      | 12/11 | 09:00–11:00 |
| Jornada  | Iniciação científica no IFPB   | Palestra     | Auditório     | 12/11 | 10:00–11:30 |
| Jornada  | Sessão de pôsteres             | Apresentação | Sala 203      | 13/11 | 14:00–17:00 |
| Egressos | Roda de conversa com egressos  | Palestra     | Auditório     | 05/12 | 19:00–21:00 |

Sobreposições propositais:

- **Mesmo horário, salas distintas:** *Abertura* (Auditório, 9h–10h30) e *Oficina de Django*
  (Laboratório 1, 10h–12h) se sobrepõem das 10h às 10h30. Serve para o conflito na agenda do
  participante dentro do mesmo evento (critério 18).
- **Mesma sala, horários que não se cruzam:** *Oficina de Django* (10h–12h) e *Git na prática*
  (14h–16h), ambas no Laboratório 1.
- **Eventos diferentes no mesmo horário:** *Projetos dos alunos* (Semana, 9h–11h) e
  *Iniciação científica no IFPB* (Jornada, 10h–11h30), em 12/11. Serve para o conflito entre
  eventos (critério 19).
- **Sala com capacidade 2:** *Oficina de Django* e *Git na prática* lotam com carla e diego
  (critérios 16 e 17).

## Roteiro rápido de verificação

1. **Anônimo:** abra `/` e a programação de um evento; tente se inscrever e você irá para o login.
2. **ana:**
   - crie um evento em *Meus eventos*; o organizador é preenchido sozinho;
   - em *Nova atividade* da Semana, tente:
     - uma atividade fora do período;
     - uma com o fim antes do início;
     - uma no Laboratório 1 às 11h;
     - uma no Laboratório 1 às 12h, que deve ser aceita.
3. **bruno:**
   - abra `/eventos/1/editar/` e `/eventos/1/painel/` (a Semana é o evento 1): os dois dão *Acesso negado*.
4. **carla:**
   - inscreva-se na Semana, na Oficina de Django e na Abertura; a Abertura é recusada por conflito;
   - inscreva-se na Jornada e em *Projetos dos alunos* e depois em *Iniciação científica*; esta é recusada por conflito entre eventos;
   - tente o Encontro de Egressos: as inscrições estão fechadas.
5. **diego:** inscreva-se na Semana e na Oficina; a sala lota e o botão some para os demais.
6. Use *Minha agenda* para ver e cancelar inscrições, e cancele o evento inteiro para sair de todas as atividades.
7. Volte como **ana** e abra o *Painel de inscritos* da Semana.

## Decisões de modelagem

- `InscricaoAtividade` se liga a **`InscricaoEvento`** (e não diretamente ao usuário):
  - **RN4 é estrutural:** não existe inscrição em atividade sem inscrição no evento.
  - **RN5 vem do `on_delete=CASCADE`:** cancelar o evento apaga as atividades junto.
  - **Sobra uma única validação de coerência:** a atividade precisa ser do mesmo evento da inscrição.
- **Vagas restantes nunca são guardadas.** São calculadas no banco com
  `F('sala__capacidade') - Count('inscricoes')` (`Atividade.objects.com_vagas()`).
- **Sobreposição de horários:** dois intervalos se sobrepõem quando `inicio_a < fim_b` e `inicio_b < fim_a`.
  - Atividades que apenas se encostam (uma termina quando a outra começa) não conflitam.
  - A mesma regra serve à RN2 (agenda do participante, consultada a partir do participante) e à RN3 (sala ocupada).
- **As regras de negócio ficam no `clean()` dos models** e são verificadas no servidor, no momento do envio.
  - Valem também no Admin.
  - Na inscrição em atividade, a linha da atividade é travada com `select_for_update()` durante a contagem de vagas.
- **Autorização:**
  - **Decoradores** (`@login_required`, `@permission_required`, `@require_POST`) nas views-função de inscrição, cancelamento e *Meus eventos*.
  - **Mixins** (`LoginRequiredMixin`, `PermissionRequiredMixin`, `UserPassesTestMixin`) nas views de classe.
  - **Permissão ≠ posse:** ser organizador não basta para editar; é preciso ser o dono do evento.
  - Nenhuma verificação usa `is_superuser`; por isso o próprio `admin` é barrado em eventos alheios.

## API REST

A API vive sob `/api/` e atende clientes sem navegador: um aplicativo, um painel em React ou um script.

- **Documentação navegável:** [`/api/docs/`](http://localhost:8000/api/docs/) (Swagger). O botão *Authorize* aceita `Token <chave>`.
- **Schema OpenAPI:** `/api/schema/`.
- **API navegável do DRF:** `/api/`.

### Endpoints

| Método | Endpoint | Quem pode | O que faz |
|--------|----------|-----------|-----------|
| GET | `/api/eventos/` | qualquer um | Lista de eventos (paginada) |
| GET | `/api/eventos/{id}/` | qualquer um | Programação: evento + atividades com nome da sala e vagas restantes |
| POST | `/api/eventos/` | organizador | Cria evento; o organizador é quem enviou o token |
| PUT/PATCH/DELETE | `/api/eventos/{id}/` | organizador dono | Altera ou exclui o evento |
| GET | `/api/atividades/` | qualquer um | Lista paginada; `?search=` (título/descrição), `?ordering=data_hora_inicio`, `?evento={id}` |
| GET | `/api/atividades/{id}/` | qualquer um | Uma atividade |
| POST | `/api/atividades/` | organizador dono do evento | Cria atividade |
| PUT/PATCH/DELETE | `/api/atividades/{id}/` | organizador dono do evento | Altera ou exclui a atividade |
| GET | `/api/salas/` | qualquer um | Salas (só leitura; são cadastradas no Admin) |
| POST | `/api/token/` | qualquer um | Troca usuário e senha pelo token |
| GET | `/api/inscricoes/` | autenticado | Minhas inscrições em eventos |
| POST | `/api/inscricoes/` | autenticado | `{"evento": id}`: inscreve-me no evento |
| DELETE | `/api/inscricoes/{id}/` | dono da inscrição | Cancela a inscrição no evento e, junto, as das atividades |
| POST | `/api/inscricoes-atividade/` | autenticado | `{"atividade": id}`: inscreve-me na atividade |
| DELETE | `/api/inscricoes-atividade/{id}/` | dono da inscrição | Cancela a inscrição na atividade (a vaga volta) |
| GET | `/api/agenda/` | autenticado | Minhas atividades, de todos os eventos, por data e hora |

Códigos de resposta:

| Situação | Código |
|----------|--------|
| Sem token em endpoint fechado | 401 |
| Token de quem não pode | 403 |
| Regra de negócio violada | 400, com a mensagem em JSON (`{"non_field_errors": [...]}` ou erro por campo) |

### Onde as regras de negócio moram, e por quê

A pergunta da atividade era: se alguém mandar um POST para a API, as cinco regras continuam valendo?
A resposta escolhida foi **mover cada regra para um lugar que as duas portas enxergam**, em vez de
reescrevê-las nos serializers. Nenhuma regra está escrita duas vezes.

| Regra | Onde mora | Como o site chega lá | Como a API chega lá |
|-------|-----------|----------------------|---------------------|
| RN1: capacidade | `InscricaoAtividade.clean()` | `servicos.inscrever_na_atividade()` → `full_clean()` | a mesma função de serviço |
| RN2: conflito do participante | `InscricaoAtividade.clean()` | idem | idem |
| RN3: sala ocupada | `Atividade.clean()` | `ModelForm` → `full_clean()` | serializer → `ValidacaoDoModelMixin` → `full_clean()` |
| RN4: inscrição prévia no evento | `servicos.inscrever_na_atividade()` (e, estruturalmente, a FK obrigatória para `InscricaoEvento`) | a função de serviço | a mesma função de serviço |
| RN5: cancelamento em cascata | `on_delete=CASCADE` em `InscricaoAtividade.inscricao_evento` | `servicos.cancelar_inscricao_evento()` → `delete()` | a mesma função de serviço |

- **Models:** guardam as regras sobre **os dados**. Valem para qualquer caminho que chame `full_clean()`, inclusive o Admin.
- **[`eventos/servicos.py`](eventos/servicos.py):** guarda as regras sobre **a operação**, como inscrição prévia, posse da inscrição e duplicidade.
  - Antes, essa lógica estava nas views HTML; ela foi extraída, e o site passou a chamar o serviço sem mudar de comportamento.
- **Por que não validar no serializer:** o `ModelSerializer` do DRF **não chama o `clean()` do model**. O `ValidacaoDoModelMixin` ([`api/serializers.py`](api/serializers.py)) faz o serializer chamar `full_clean()`, para que a regra continue escrita só no model.
- **Tradução dos erros:** as regras levantam o `ValidationError` do Django. O exception handler em [`api/excecoes.py`](api/excecoes.py) o converte, num lugar só, em `400` com JSON. Sem isso, uma regra violada pela API viraria erro 500.
- **Dados que nunca vêm do cliente:**
  - organizador e participante não são campos dos serializers; vêm de `request.user`;
  - vagas restantes são calculadas por `Atividade.objects.com_vagas()`;
  - a lógica de negócio recebe `serializer.validated_data`, nunca `request.data`.

### ViewSet ou view-função: onde e por quê

- **`ModelViewSet` + router** para **eventos** e **atividades**, e `ReadOnlyModelViewSet` para **salas**.
  - São recursos com CRUD completo e regular (listar, detalhar, criar, alterar, excluir). O router gera as cinco rotas de uma vez.
  - Paginação, busca, ordenação e permissões entram como configuração.
- **`@api_view`** para **inscrições, cancelamentos e agenda**. Não são CRUD de um recurso, mas **operações**:
  - "inscrever-me" não aceita `PUT`;
  - "cancelar" de outra pessoa é proibido;
  - "agenda" é uma consulta sob medida do usuário.
  
  Uma view-função curta deixa explícito o fluxo: validar a entrada, chamar o serviço e responder com o código certo. Num ViewSet, seria preciso desligar ações que não fazem sentido.

### O teste que vale mais (seção 8)

Regra escolhida: **RN1, capacidade da sala.** carla e diego ocuparam as duas vagas da *Oficina de Django*
(Laboratório 1, capacidade 2). Depois, bruno tentou a terceira vaga com `curl`:

```bash
curl -i -X POST http://localhost:8000/api/inscricoes-atividade/ \
     -H "Authorization: Token c83b2c2c0456d817dc37f1b5a199e46474c541a9" \
     -H "Content-Type: application/json" -d '{"atividade": 2}'
```

| Pergunta | Resposta |
|----------|----------|
| Código HTTP | `400 Bad Request` |
| Corpo | `{"non_field_errors":["Esta atividade está lotada."]}` |
| Arquivo e método | `eventos/models.py`, `InscricaoAtividade.clean()`, chamado por `eventos/servicos.py`, `inscrever_na_atividade()` |
| O site usa o mesmo código? | **Sim.** A view HTML `inscrever_atividade` (`eventos/views.py`) chama a mesma `servicos.inscrever_na_atividade()`, que chama o mesmo `clean()`. A mensagem que aparece na tela é a mesma string. |

### Desafio opcional: a programação em uma requisição

`GET /api/eventos/{id}/` devolve o evento, as atividades, a sala de cada uma e as vagas restantes,
com serializers aninhados. Usa `prefetch_related` com `Atividade.objects.com_vagas().select_related('sala')`.

Medição com `CaptureQueriesContext`:

| Atividades no evento | Consultas ao banco |
|---------------------:|-------------------:|
| 4  | 2 |
| 24 | 2 |

## Testes automatizados

### Como rodar

```bash
python manage.py test                                  # suíte inteira
python manage.py test --shuffle                        # em ordem aleatória
python manage.py test eventos.tests.test_models        # só um arquivo
python manage.py test -v 2                             # com o nome de cada teste
coverage run manage.py test && coverage report         # cobertura
```

**Números:** 163 testes, 0,52 s para rodar e 0,83 s contando a criação do banco de teste.
Passam com `--shuffle` (três sementes diferentes conferidas) e sem o `db.sqlite3`. Nenhum teste é pulado.

### Organização

O pacote [`eventos/tests/`](eventos/tests/) substituiu o antigo `tests.py`.

| Arquivo | Testes | O que cobre |
|---------|-------:|-------------|
| `base.py` | — | Cenário compartilhado, montado em `setUpTestData`, com o mapa no docstring; helpers de site e API |
| `test_models.py` | 35 | RF4 (dados inválidos com `full_clean()` + `assertRaises`) e as regras que moram no model |
| `test_forms.py` | 13 | RF9: formulários instanciados sem view (`is_valid()`, `errors`, `cleaned_data`) |
| `test_views.py` | 56 | Site: RF5 a RF8, RF12 e as cinco regras pela porta HTML |
| `test_api.py` | 49 | API: RF10, RF11 e as cinco regras pela porta da API |
| `test_comandos.py` | 10 | O `popular_dados` cria o que este README promete (veja o Desafio B) |

Decisões que valem para a suíte inteira:

- **Os dados vêm do próprio teste.** O cenário é criado no banco de teste. A suíte antiga usava o `popular_dados`; agora ele só aparece em `test_comandos.py`, onde é o objeto do teste.
- **Hash de senha rápido.** O `Cenario` usa o hash MD5, com `@override_settings`. O PBKDF2 padrão é lento de propósito: a suíte antiga levava 7 s para 37 testes.
- **API com token de verdade.** Os testes da API mandam o cabeçalho `Authorization: Token ...`, sem `force_authenticate`, para exercitar a autenticação que um cliente real usa.
- **Endereços com `reverse()`.** Nenhum endereço escrito à mão, nenhum `sleep` e nenhum `skip`.

### As cinco regras nas duas portas (RF2 e RF3)

| Regra | Site: aceito / recusado | API: aceito / recusado |
|-------|-------------------------|------------------------|
| RN1: capacidade | `test_rn1_inscricao_com_vaga_e_aceita_e_vagas_diminuem` / `test_rn1_inscricao_alem_da_capacidade_e_recusada` | `test_rn1_inscricao_com_vaga_responde_201_e_vagas_diminuem` / `test_rn1_inscricao_alem_da_capacidade_responde_400` |
| RN2: conflito do participante | `test_rn2_atividade_em_outro_horario_e_aceita` / `test_rn2_atividade_simultanea_e_recusada`, `..._de_outro_evento_e_recusada` | `test_rn2_atividade_em_outro_horario_responde_201` / `test_rn2_atividade_simultanea_responde_400`, `..._de_outro_evento_responde_400` |
| RN3: sala ocupada | `test_rn3_mesma_sala_em_outro_horario_e_aceita` / `test_rn3_sala_ocupada_e_recusada_com_mensagem` | `test_rn3_mesma_sala_em_outro_horario_responde_201` / `test_rn3_sala_ocupada_responde_400_com_mensagem` |
| RN4: inscrição prévia | `test_rn4_quem_esta_no_evento_se_inscreve_na_atividade` / `test_rn4_quem_nao_esta_no_evento_e_recusado` | `test_rn4_quem_esta_no_evento_se_inscreve_na_atividade` / `test_rn4_quem_nao_esta_no_evento_responde_400` |
| RN5: cascata | `test_rn5_cancelar_evento_cancela_as_atividades_dele` / `test_rn5_cancelar_evento_preserva_atividades_de_outros_eventos` | `test_rn5_cancelar_evento_cancela_as_atividades_dele` / `test_rn5_cancelar_evento_preserva_atividades_de_outros_eventos` |

São 12 cenários de recusa: 6 no site e 6 na API.

- **Mais testes no nível do model:** `test_models.py` testa as mesmas regras sem HTTP, incluindo os cinco casos de sobreposição e os dois de intervalos que só se encostam.
- **No RN5, "recusado" significa "não pode passar do limite":** cancelar um evento não pode levar junto as inscrições de outro evento.

### A tabela de sabotagem

Cada sabotagem foi aplicada **sozinha**: alterar o código, rodar a suíte inteira, registrar o resultado e desfazer.
A coluna "Onde mexer" descreve a alteração exata, para que qualquer linha possa ser refeita à mão.
O resultado abaixo é o da rodada final, sobre o código entregue.

| Sabotagem | Onde mexer | Teste que falhou | Verde na 1ª rodada? |
|-----------|------------|------------------|---------------------|
| 1. Capacidade da sala | `eventos/models.py`, `InscricaoAtividade.clean()`: comentar o `if inscritos >= atividade.sala.capacidade` e o `raise` | `test_models.CapacidadeTests.test_inscricao_alem_da_capacidade_e_recusada`, `test_views.RegrasPeloSiteTests.test_rn1_inscricao_alem_da_capacidade_e_recusada`, `test_api.RegrasPelaApiTests.test_rn1_inscricao_alem_da_capacidade_responde_400` (3 F) | não |
| 2. Horário sobreposto do participante | `eventos/models.py`, `InscricaoAtividade.clean()`: comentar o `if conflito:` e o `raise` | `ConflitoDoParticipanteTests` (2), `RegrasPeloSiteTests.test_rn2_atividade_simultanea_*` (2), `RegrasPelaApiTests.test_rn2_atividade_simultanea_*` (2) (6 F) | não |
| 3. Sala ocupada | `eventos/models.py`, `Atividade.clean()`: comentar o `if conflito:` e o `raise` | `SalaOcupadaTests` (os 5 subtestes de sobreposição + entre eventos), `test_forms.AtividadeFormTests.test_sala_ocupada_gera_erro_no_campo_sala`, `RegrasPeloSiteTests.test_rn3_sala_ocupada_e_recusada_com_mensagem`, `RegrasPelaApiTests.test_rn3_sala_ocupada_responde_400_com_mensagem` (9 F) | não |
| 4. Inscrição prévia no evento | `eventos/servicos.py`, `inscrever_na_atividade()`: comentar o `if inscricao_evento is None:` e o `raise` | `RegrasPeloSiteTests.test_rn4_quem_nao_esta_no_evento_e_recusado`, `RegrasPelaApiTests.test_rn4_quem_nao_esta_no_evento_responde_400` (2 **E**) | não |
| 5. Cancelar o evento sem cancelar as atividades | `eventos/models.py`, `InscricaoAtividade.inscricao_evento`: `on_delete=models.CASCADE` → `models.DO_NOTHING` | `CancelamentoEmCascataTests` (2), `RegrasPeloSiteTests.test_rn5_*` (2), `RegrasPelaApiTests.test_rn5_*` (2), `CancelamentosPeloSiteTests.test_cancelar_evento_redireciona_e_avisa_quantas_atividades_sairam` (4 F + 7 **E**) | não |
| 6. `render` no lugar do `redirect` | `eventos/views.py`, `inscrever_evento()`: `return redirect(...)` → `return render(request, 'eventos/evento_detail.html', {'evento': evento})` | `test_views.InscricaoNoEventoPeloSiteTests.test_inscricao_grava_no_banco_redireciona_e_avisa` (1 F) | não |
| 7. Verificação de dono na edição do evento | `eventos/views.py`, `EventoUpdateView`: tirar `EventoDoOrganizadorMixin` das bases e pôr `model = Evento` na classe | `test_views.AutorizacaoTests.test_organizador_nao_edita_evento_de_outro`, `test_nem_o_superusuario_edita_evento_de_outro` (2 F) | não |
| 8. Campo indevido no serializer público | `api/serializers.py`, `EventoSerializer.Meta.fields`: acrescentar `'organizador'` | `test_api.PortaAbertaTests.test_evento_publico_traz_exatamente_os_campos_esperados`, `test_programacao_publica_traz_exatamente_os_campos_esperados`, `test_porta_aberta_nao_expoe_organizador_nem_inscritos` (4 F) | não |
| 9. Sem `select_related` na programação | `eventos/views.py`, `EventoDetailView.get_context_data()`: tirar o `.select_related('sala')` | `test_views.ConsultasDaProgramacaoTests.test_programacao_para_anonimo_tem_consultas_constantes`, `test_programacao_para_participante_tem_consultas_constantes` (2 F) | não |

**Sobre "nenhuma verde na 1ª rodada":** os testes foram escritos **depois** de ler a lista de sabotagens. Pegar as
nove era esperado, e por isso esse resultado sozinho prova pouco. O que a rodada ensinou está nos detalhes:

- **A sabotagem 7 foi refeita.** Na primeira tentativa, tirar o mixin removeu também o `model` e o `get_object()` que ele fornecia. A view inteira quebrou (3 E, inclusive o teste do dono editando o próprio evento). Era uma sabotagem infiel, que testava "a view existe", e não "a posse é verificada". Na versão correta, com `model = Evento` mantido, falham exatamente os dois testes de posse, e o do dono continua verde.
- **A sabotagem 7 também revelou uma regra escrita em quatro lugares.** Tirar a checagem do site não derrubou nenhum teste da API, porque a API tinha a própria cópia (veja abaixo).
- **A sabotagem 4 dá E, e não F.** Sem a checagem, o código seguinte acessa `inscricao_evento.inscricoes_atividade` com `None` e quebra com `AttributeError`, um erro 500.
  - O dado continua protegido: a FK obrigatória de `InscricaoAtividade` para `InscricaoEvento` não deixa gravar inscrição em atividade sem inscrição no evento. É a RN4 estrutural da modelagem.
  - Mas o usuário veria uma página de erro em vez da mensagem. O teste falha "do jeito errado" porque é o código que quebrou, não a asserção.
- **A sabotagem 5 também gera E.** Com `DO_NOTHING`, a inscrição em atividade fica apontando para uma inscrição no evento que não existe mais. O SQLite rejeita isso na checagem de chave estrangeira que o `TestCase` faz ao final de cada teste, com `IntegrityError`.

### Sabotagens extras: as que passaram verdes

Como as nove foram pegas, procuramos alterações que um colega poderia fazer com pressa. A pista veio das linhas
que o `coverage` apontou como nunca executadas. Estas **passaram verdes** na primeira rodada:

| Sabotagem | Onde mexer | Verde na 1ª rodada? | Teste acrescentado (que agora falha) |
|-----------|------------|---------------------|--------------------------------------|
| 10. Dono na edição de **atividade** | `eventos/views.py`, `AtividadeUpdateView`: acrescentar `def test_func(self): return True` | **sim** | `AutorizacaoTests.test_organizador_nao_edita_atividade_de_evento_de_outro` (+ exclusão, dono editando e o equivalente na API) |
| 11. Checagem "já inscrito nesta atividade" | `eventos/servicos.py`: comentar o `if ...inscricoes_atividade.filter(atividade=atividade).exists()` | **sim** | `RegrasPeloSiteTests.test_repetir_a_mesma_atividade_e_recusado_com_mensagem_propria` e `RegrasPelaApiTests.test_repetir_a_mesma_atividade_responde_400_com_mensagem_propria` |
| 12. `raise_exception` da *Meus eventos* | `eventos/views.py`, `meus_eventos`: tirar o `raise_exception=True` | **sim** | `AutorizacaoTests.test_participante_que_abre_meus_eventos_recebe_403_e_nao_volta_ao_login` |

O que cada uma significava:

- **10:** qualquer organizador editaria atividades de eventos alheios pelo site. O RF8 só pedia o teste do *evento*, e a atividade ficou descoberta.
- **11:** a duplicata continuava barrada pela `UniqueConstraint`, mas com a mensagem genérica do Django 4.2.
- **12:** um participante seria mandado de novo para o login, mesmo já estando logado.

### Cobertura

**97%** do código do projeto, sem contar migrations, testes, `manage.py`, `asgi` e `wsgi` (`.coveragerc`).

Antes das sabotagens extras e do Desafio B, a cobertura era de **88%**. As três sabotagens que passaram
verdes moravam em código coberto ou quase coberto:

- **10:** a `AtividadeUpdateView` aparecia nas linhas sem cobertura, mas a falha era de **asserção**, não de execução. Um teste que só fizesse GET como dono cobriria a view inteira e continuaria verde com a checagem de posse removida.
- **11:** a linha 55 do `servicos.py` não era executada. E executá-la não bastaria: só a asserção sobre a **mensagem** distingue a checagem própria da `UniqueConstraint`.
- **12:** a linha alterada, o decorador `@permission_required(..., raise_exception=True)`, aparecia como **coberta**, porque decoradores rodam quando o módulo é importado. O relatório não tinha como mostrar que nenhum teste fazia o caminho do participante logado. O único teste da view era o do anônimo, que nem entra no corpo da função.

Ou seja, 88% nunca significou "88% das regras protegidas". A cobertura mede o que foi **visitado**; a sabotagem
mede o que foi **afirmado**. A sabotagem 12 é a prova mais clara: a linha sabotada estava marcada como coberta,
e nenhum teste percebeu a mudança.

O que ainda está fora dos 97%:

- **`__str__` dos models e o painel do Admin:** não têm regra.
- **`servicos.py:28-30`:** o `except IntegrityError` de duas inscrições quase simultâneas no mesmo evento.
- **`GET /api/inscricoes/`:** a listagem nunca é chamada pelos testes.

O primeiro buraco conhecido é este: tirar o `except IntegrityError` passaria verde. Para fechá-lo, o teste
precisaria simular a corrida com `unittest.mock.patch`, fazendo a checagem de duplicata devolver `False` para
forçar o `IntegrityError` do banco.

### Regras escritas em dois lugares

- **As cinco regras de negócio:** já estavam num lugar só desde a atividade 06.
  - A refatoração para [`eventos/servicos.py`](eventos/servicos.py) tirou a RN4 e o fluxo de inscrição das views HTML.
  - RN1, RN2 e RN3 ficam no `clean()` dos models, chamado pelo `ModelForm`, pelos serviços e pelo `ValidacaoDoModelMixin` dos serializers.
  - O RF3 confirmou isso: as sabotagens 1 a 4 derrubaram testes **das duas portas ao mesmo tempo**.
- **A verificação de posse do evento estava escrita em quatro lugares.** Ela não é uma das cinco regras, mas é uma regra de autorização:
  - o mixin `OrganizadorDoEventoMixin` e o `eh_organizador` da programação, no site;
  - a permission `EhOrganizadorDoEventoOuSomenteLeitura` e o `validate_evento` do serializer, na API.
  
  Quem mostrou foi a sabotagem 7, que só derrubou testes do site. Agora existe um único `Evento.organizado_por(usuario)`, usado pelas duas portas.

### Desafio B: a sabotagem que inventamos

**Sabotagem:** no `popular_dados`, mudar a capacidade do Laboratório 1 de `2` para `20`.

- **Por que nenhum teste pegava:** o comando tinha **0% de cobertura**. Os testes criam os próprios dados, como a restrição técnica 3 exige, então nada rodava o comando.
- **Por que importa:** o `db.sqlite3` entregue e o mapa de dados deste README dependem dele. Com a mudança, a sala "pequena" deixa de ser pequena. Os critérios de capacidade (lotar a sala com carla e diego) não podem mais ser demonstrados, e nenhum teste avisa.
- **Teste que fecha o buraco:** [`test_comandos.py`](eventos/tests/test_comandos.py) roda o comando no banco de teste e confere:
  - as cinco contas, com papéis, senhas e tokens deste README;
  - a sala de capacidade 2;
  - os eventos que se cruzam e o evento fechado;
  - os três pares de atividades sobrepostas;
  - que o banco sai sem inscrições, que rodar de novo não duplica nada e que o `--limpar` funciona.
  
  Com a sabotagem, falham 3 testes.

## Requisitos pendentes

- **Site (Ponto Extra II):** nenhum. Todos os requisitos, regras, restrições e critérios foram implementados. O desafio opcional (lista de espera) não foi feito.
- **API (Atividade 06):** nenhum. RF1 a RF11, as restrições técnicas e os 25 critérios foram conferidos, e o desafio opcional foi feito.
- **Testes (Atividade 08):** nenhum. RF1 a RF13 e os 16 critérios de aceitação foram cumpridos, e o Desafio B foi feito. O Desafio A (teste antes da implementação) não foi feito.
