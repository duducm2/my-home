# Orçamento projetado (takeoff × mediana)

Gerado em: 2026-09-18 13:20:34

- **Projetado total:** R$ 413.619,61
- Materiais: R$ 300.469,61
- Serviços / taxas únicas: R$ 113.150,00

## Medidas derivadas

- `floor_area_m2`: 50.56
- `wall_area_gross_m2`: 199.962
- `wall_area_net_m2`: 177.482
- `opening_area_m2`: 22.48
- `building_footprint_m2`: 54.1134
- `interior_door_count`: 6
- `window_count`: 6
- `habitable_room_count`: 6
- `wall_height_m`: 2.7
- `gantt_porcelain_scope_m2`: 115.0

## Premissas

- Interior useful floor area from house.json (50.56 m²) drives floor finishes.
- Wall area is estimated from room floor footprints × wall height 2.7 m using perimeter proxies, minus openings.
- Porcelain waste factor 10%; paint assumes ~12 m²/L theoretical coverage with 2 coats → ~6 m²/L effective.
- Structural bulk (cimento/areia/tijolo) uses low-confidence heuristics for a light retrofit, not a full structural BOM.
- Services and one-time fees are excluded from takeoff (qty remains 1).
- Gantt text hints: ~115 m² porcelanato scope and 5 janelas inform overrides where noted.

## Linhas (materiais por custo projetado)

- **Madeiramento ou estrutura metálica**: qtd 54.1134 × R$ 4500.00 = R$ 243510.30 (estimated; building_footprint)
- **Conduítes**: qtd 126.4 × R$ 117.50 = R$ 14852.00 (estimated; floor×conduit)
- **Rejunte de porcelanato**: qtd 138.0 × R$ 51.95 = R$ 7168.41 (estimated; porcelain×grout)
- **Porcelanato**: qtd 115.0 × R$ 42.90 = R$ 4933.50 (estimated; gantt_porcelain_scope_m2)
- **Janela (quartos e escritório)**: qtd 5.0 × R$ 754.12 = R$ 3770.60 (estimated; fixed_units)
- **Portas internas**: qtd 6.0 × R$ 365.42 = R$ 2192.52 (estimated; interior_door_count)
- **Rodapés para acompanhar o porcelanato (R$1500)**: qtd 28.4422 × R$ 75.99 = R$ 2161.32 (estimated; approx_perimeter)
- **Telha**: qtd 935.0796 × R$ 2.15 = R$ 2010.42 (estimated; footprint×tiles×waste)
- **Dispositivos de segurança**: qtd 1.0 × R$ 2000.00 = R$ 2000.00 (estimated; fixed_units)
- **Porta Balcão (R$2000)**: qtd 1.0 × R$ 1903.41 = R$ 1903.41 (measured; fixed_units)
- **Argamassa para o porcelanato**: qtd 40.25 × R$ 41.40 = R$ 1666.35 (estimated; porcelain×mortar)
- **Areia grossa, fina e pedrisco**: qtd 6.0 × R$ 254.45 = R$ 1526.70 (estimated; fixed_units)
- **Tinta**: qtd 2.0 × R$ 739.90 = R$ 1479.80 (estimated; wall_net / coverage -> cans)
- **Cimento**: qtd 40.0 × R$ 35.90 = R$ 1436.00 (estimated; fixed_units)
- **Box de vidro para o banheiro (R$850)**: qtd 2.0 × R$ 709.00 = R$ 1418.00 (estimated; fixed_units)
- **Tijolinho de barro**: qtd 800.0 × R$ 1.33 = R$ 1068.00 (estimated; fixed_units)
- **Caçamba de entulho**: qtd 3.0 × R$ 350.00 = R$ 1050.00 (estimated; fixed_units)
- **Torneiras**: qtd 6.0 × R$ 157.40 = R$ 944.40 (estimated; fixed_units)
- **Vaso**: qtd 2.0 × R$ 399.95 = R$ 799.90 (estimated; fixed_units)
- **Impermeabilizante (bianco)**: qtd 2.0 × R$ 319.90 = R$ 639.80 (estimated; fixed_units)
- **Vitrô Sala**: qtd 1.0 × R$ 520.00 = R$ 520.00 (measured; fixed_units)
- **Pias e bancadas**: qtd 2.0 × R$ 251.90 = R$ 503.79 (estimated; fixed_units)
- **Calhas e rufos**: qtd 24.0 × R$ 20.79 = R$ 498.96 (estimated; fixed_units)
- **Caixa de água**: qtd 1.0 × R$ 449.95 = R$ 449.95 (measured; fixed_units)
- **Tomadas**: qtd 24.0 × R$ 17.05 = R$ 409.20 (estimated; rooms×outlets)
