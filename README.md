# Eventos do Campus

Sistema de inscrições em eventos do campus, desenvolvido em Django 4.2 como atividade de Ponto Extra II
da disciplina de Rapid Application Development (RAD), Tecnólogo em Sistemas para Internet, IFPB.

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

## Requisitos pendentes

Nenhum: todos os requisitos funcionais (RF1–RF10), regras de negócio (RN1–RN5), restrições técnicas
e critérios de aceitação foram implementados. O desafio opcional (lista de espera) não foi feito.
