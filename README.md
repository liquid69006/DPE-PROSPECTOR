# DPE-PROSPECTOR

Dashboard prospection copropriétés (DVF × RNC × BDNB), onglet
**Secteur Prospector** servi par Cloudflare Worker.

📋 **Stratégie & conventions du pipeline secteur** :
[`data/PIPELINE.md`](data/PIPELINE.md) — architecture
make_light (hors dépôt) → correctifs additifs versionnés, contrat
non-destructif, décision surgical-vs-regen, chaîne ordonnée des
correctifs, règles de calcul `renderSecteur`, vérification
`test_render_secteur.js`. **À lire avant toute modif data/pipeline.**