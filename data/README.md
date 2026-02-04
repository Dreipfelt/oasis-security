# 📁 Dossier des Données

## ⚠️ Important

Les fichiers de données ne sont **pas inclus** dans ce repository pour des raisons de taille.

## 📥 Téléchargement

1. Rendez-vous sur [data.gouv.fr](https://www.data.gouv.fr/)
2. Recherchez : `statistiques criminalité départements` ou `séries chronologiques sécurité publique`
3. Téléchargez le fichier CSV
4. Renommez-le en : `serieschrono-datagouv.csv`
5. Placez-le dans ce dossier (`data/`)

## 📋 Format Requis

Le fichier doit être au format CSV avec séparateur `;` et encoding `latin-1`.

### Colonnes obligatoires :

| Nom | Type | Description |
|-----|------|-------------|
| `Unite_temps` | Integer | Année (ex: 2023) |
| `Zone_geographique` | String | Département (ex: "75-Paris") |
| `Valeurs` | Integer | Nombre de cas |
| `Indicateur` | String | Type d'infraction |

### Colonne optionnelle :

| Nom | Type | Description |
|-----|------|-------------|
| `Code_dep` | String | Code département (ex: "75") |

> 💡 Si `Code_dep` est absent, il sera automatiquement extrait de `Zone_geographique`.

## 🔗 Liens Utiles

- [data.gouv.fr - Données de sécurité](https://www.data.gouv.fr/fr/datasets/?q=s%C3%A9curit%C3%A9+d%C3%A9partement)
- [Ministère de l'Intérieur - Statistiques](https://www.interieur.gouv.fr/Interstats)