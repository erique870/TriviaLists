from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.domain.enums import TipoCardapio
from app.domain.exceptions import ValidacaoDeDominioError
from app.domain.lista_diaria import ListaDiaria
from app.domain.produto import Produto


@dataclass(slots=True)
class Restaurante:
    id: int
    nome: str
    endereco: str
    horario_padrao_abertura: time
    horario_padrao_fechamento: time
    tipo_cardapio: TipoCardapio
    produtos: dict[int, Produto] = field(default_factory=dict)
    listas: list[ListaDiaria] = field(default_factory=list)
    ativo: bool = True

    def obter_tipo_cardapio(self) -> TipoCardapio:
        return self.tipo_cardapio

    def criar_lista_diaria(
        self,
        lista_id: int,
        dia: date,
        produtos: list[Produto],
        publicada_em: datetime,
        horario_abertura: time | None = None,
        horario_fechamento: time | None = None,
    ) -> ListaDiaria:
        if not self.ativo:
            raise ValidacaoDeDominioError(
                "Restaurante inativo não pode publicar cardápio.",
                codigo="restaurante_inativo",
            )

        abertura = datetime.combine(
            dia, horario_abertura or self.horario_padrao_abertura, tzinfo=publicada_em.tzinfo
        )
        fechamento = datetime.combine(
            dia, horario_fechamento or self.horario_padrao_fechamento, tzinfo=publicada_em.tzinfo
        )
        if fechamento <= abertura:
            raise ValidacaoDeDominioError("Fechamento deve ocorrer após a abertura.")
        corte_padrao = datetime.combine(dia, self.horario_padrao_fechamento, tzinfo=publicada_em.tzinfo)
        if dia == publicada_em.date() and self.tipo_cardapio == TipoCardapio.VARIAVEL and publicada_em >= corte_padrao:
            fechamento = publicada_em + timedelta(minutes=30)
        if fechamento <= publicada_em:
            raise ValidacaoDeDominioError("O horário de fechamento já foi ultrapassado.", codigo="fechamento_no_passado")

        lista = ListaDiaria(
            id=lista_id,
            restaurante_id=self.id,
            data=dia,
            horario_abertura=abertura,
            horario_fechamento=fechamento,
        )
        lista.vincular_produtos(produtos)
        self.produtos.update({produto.id: produto for produto in produtos})
        self.listas.append(lista)
        return lista

    def obter_listas_historico(self) -> list[ListaDiaria]:
        return sorted(self.listas, key=lambda lista: (lista.data, lista.id), reverse=True)
