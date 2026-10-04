"""A ruling the site lists is the cited one only if both sides of the carátula match."""

from spikes.site_lookup import is_same_case


def test_the_same_parties_are_the_same_case():
    assert is_same_case("Cáceres Francisco Ángel c/ Ambesi Ana Estela y otro s/ interdicto",
                        "CACERES, FRANCISCO ANGEL c/ AMBESI, ANA ESTELA Y OTRO s/INTERDICTO")
    assert is_same_case("Travela, Olga Beatriz c/ANSeS s/Reajustes varios",
                        "TRAVELA OLGA BEATRIZ c/ ANSES s/REAJUSTES VARIOS")


def test_sharing_words_on_one_side_only_is_another_case():
    # same bank suing other debtors; a namesake suing another ART
    assert not is_same_case("Banco Itau Buen Ayre S.A. c/ Torrellas Roberto Daniel y otros s/ Ejecutivo",
                            "BANCO ITAU BUEN AYRE S.A. c/ AGUILAR SANDRA s/EJECUTIVO")
    assert not is_same_case("Martínez, Alejandro Ernesto c/ Georgalos Hnos. S.A. s/ Juicio Sumarísimo",
                            "MARTINEZ, ERNESTO FABIAN c/ PROVINCIA ART S.A. s/RECURSO LEY 27348")
    assert not is_same_case("Cáceres Francisco Ángel c/ Ambesi Ana Estela y otro s/ interdicto",
                            "CACERES ARZA, ESTELA AGUSTINA c/ LA CENTRAL DE ESCOBAR Y OTRO s/DAÑOS")


def test_a_caratula_without_a_defendant_needs_two_words():
    assert is_same_case("Editorial Atlántida S.A. s/ concurso preventivo",
                        "EDITORIAL ATLANTIDA S.A. s/CONCURSO PREVENTIVO")
    assert not is_same_case("Editorial Atlántida S.A. s/ concurso preventivo", "EDITORIAL PERFIL S.A. s/QUIEBRA")
