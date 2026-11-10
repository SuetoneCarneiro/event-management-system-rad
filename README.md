# Eventos do Campus

Sistema de inscrições em eventos do campus, desenvolvido em Django 4.2 na disciplina de
Rapid Application Development (RAD), Tecnólogo em Sistemas para Internet, IFPB.

- **Ponto Extra II:** o site HTML.
- **Atividade 06:** a API REST, ao lado do site e sobre os mesmos models ([seção da API](#api-rest)).

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

Testes automatizados (37 testes, cobrindo os 27 critérios de aceitação):

```bash
python manage.py test eventos
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

## Requisitos pendentes

- **Site (Ponto Extra II):** nenhum. Todos os requisitos, regras, restrições e critérios foram implementados. O desafio opcional (lista de espera) não foi feito.
- **API (Atividade 06):** nenhum. RF1 a RF11, as restrições técnicas e os 25 critérios foram conferidos, e o desafio opcional foi feito.
