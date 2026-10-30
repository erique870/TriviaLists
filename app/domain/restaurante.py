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
    ) -> ListaDiaria:
        if not self.ativo:
            raise ValidacaoDeDominioError(
                "Restaurante inativo não pode publicar cardápio.",
                codigo="restaurante_inativo",
            )

        abertura = datetime.combine(
            dia, self.horario_padrao_abertura, tzinfo=publicada_em.tzinfo
        )
        fechamento = datetime.combine(
            dia, self.horario_padrao_fechamento, tzinfo=publicada_em.tzinfo
        )
        if fechamento <= abertura:
            fechamento += timedelta(days=1)
        if self.tipo_cardapio == TipoCardapio.VARIAVEL and publicada_em > fechamento:
            fechamento = publicada_em + timedelta(minutes=30)

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
