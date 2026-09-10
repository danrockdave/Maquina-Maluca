# Checklist de requisitos

Este documento detalha como cada item da avaliação foi implementado e onde procurar no código.

## Set pixel
`gfx/raster.py :: set_pixel(fb, x, y, color, clip)`. Escreve uma cor numa matriz
`numpy` de forma `(largura, altura, 3)`. Todas as primitivas chamam essa função. Nos
preenchimentos (scanline e seed fill) os *spans* horizontais são escritos com uma
atribuição de fatia (`fb[x0:x1, y] = ...`), que equivale a `set_pixel` consecutivos e
evita o custo de um laço Python por pixel.

## Primitivas de rasterização
* **Reta** – Bresenham em inteiros (`draw_line`).
* **Circunferência** – algoritmo do ponto médio com simetria de 8 pontos (`draw_circle`).
* **Elipse** – algoritmo do ponto médio em duas regiões (`draw_ellipse`).

A tela de abertura (`SplashScene._build`) usa as três: retas para rampa, balde, raios do
sol, fio do balão e dentes da engrenagem; circunferência para bola, engrenagem e sol;
elipse para o balão, seu brilho e a boca do balde. No jogo, a boca do balde é uma elipse e
a gaiola do ventilador e os rolos da esteira são circunferências em coordenadas de mundo.

## Preenchimento de regiões
* **Flood fill** (`flood_fill`) – substitui a região 4-conexa da cor da semente. Usado
  no chão da abertura (região preta abaixo da linha do horizonte).
* **Boundary fill** (`boundary_fill`) – preenche até encontrar a cor da borda. Usado na
  bola, rampa, engrenagem, balão, balde e sol da abertura.
* **Scanline** (`fill_polygon`) – tabela de arestas, interseções por linha, pares de
  cruzamentos ordenados, intervalo semiaberto para evitar contagem dupla de vértices.
  Ao longo de cada aresta e de cada span são interpolados atributos por vértice:
  cor (gradiente) ou `(u, v)` (textura).

## Transformações geométricas
`gfx/transform.py` traz matrizes 3×3 homogêneas de translação, rotação e escala e sua
composição. Cada peça tem matriz de modelo `T·R·S`. Arrastar aplica translação; Q/E e
botão direito aplicam rotação; o zoom da câmera aplica escala.

## Animação
* Pás do ventilador giram (rotação sobre o eixo do ventilador).
* Linhas de vento se deslocam (translação em função do tempo).
* Textura da esteira rola (deslocamento contínuo de `u`).
* Bola gira conforme sua velocidade horizontal.
* Engrenagens do menu principal giram.
* A explosão da dinamite é um polígono em estrela multiplicado por uma matriz de escala
  que cresce com o tempo (`TNT.local_shapes`), e os anéis do ímã são circunferências de
  raio crescente.

## Janela e viewport
`game/camera.py :: Camera`. A janela é um retângulo em coordenadas de mundo e a
viewport um retângulo em coordenadas de dispositivo. Pan = translação da janela;
zoom = escala da janela (mantendo a proporção da viewport e o ponto sob o cursor fixo).
Há duas viewports simultâneas (cena e minimapa) e o painel de peças renderiza cada
peça através de uma mini janela/viewport própria.

## Recorte de Cohen-Sutherland
`gfx/clipping.py`. Códigos de região de 4 bits, aceitação/rejeição trivial e recorte
iterativo. Toda linha em coordenadas de mundo (contornos de polígonos, linhas de vento,
borda do mundo, retângulo de seleção, janela desenhada no minimapa) passa por ele antes
de Bresenham. Basta dar zoom e arrastar a janela para ver peças cortadas na borda da
viewport.

## Mapeamento de textura
`tools/make_textures.py` gera as texturas (madeira, tijolo, metal, borracha, esteira,
papelão) e as salva como PNG; `gfx/texture.py` carrega o PNG para matriz. No scanline,
cada vértice carrega `(u, v)`; o valor é interpolado ao longo das arestas e depois ao
longo do span, e o texel correspondente é copiado para o framebuffer. Coordenadas fora
de `[0, 1)` repetem a textura (muro com 3 repetições, esteira com 3 repetições + offset).

## Entrada e menus
Teclado e mouse (incluindo roda) em `PlayScene.handle_event`. Menus: principal, seleção
de nível, ajuda, pausa, painel de inventário com pré-visualização das peças e tela de
vitória com botão de próximo nível.

## Extras: editor e gerador de fases
* **Editor** (`PlayScene` com `editor=True`): qualquer peça pode ser colocada, arrastada e
  girada; `F` alterna `Part.fixed`. Ao salvar, `Level.to_dict` transforma as peças travadas
  em cenário e conta as soltas como inventário. O arquivo JSON fica em `levels/custom/`.
* **Gerador** (`game/generator.py`): sorteia bola e balde, constrói uma escada de tábuas
  entre eles, roda a física (`simulate`) até a bola cair ou chegar ao balde, adiciona
  obstáculos que mantêm a solução e esconde metade das tábuas. A semente aparece no nome
  da fase para reprodução.
