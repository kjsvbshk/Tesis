# NOTICE — Avisos de Atribución y Terceros

Este archivo forma parte del Trabajo de Grado titulado
**"Sistema de Predicciones y Apuestas Virtuales NBA basado en Machine Learning"**

**Autores**: Irving Rios Ramirez, Jhon Edison Montaño Parra
**Institución**: Universidad Manuela Beltrán (UMB), Bogotá, Colombia
**Año**: 2026

---

## 1. Licencias de Este Proyecto

| Componente | Licencia |
|-----------|---------|
| Código fuente (Backend, Frontend, ML, Scrapping) | MIT License — ver `LICENSE` |
| Documentación (README, guías, diagramas) | CC BY 4.0 — ver `LICENSE-CC` |

---

## 2. Dependencias de Código Abierto

Este proyecto hace uso de las siguientes bibliotecas y frameworks de código
abierto. Se reconoce y agradece el trabajo de sus respectivos autores y
comunidades.

### Backend (Python)

| Biblioteca | Versión | Licencia | Autores / Mantenedores |
|-----------|---------|---------|----------------------|
| FastAPI | 0.104.1 | MIT | Sebastián Ramírez (tiangolo) |
| SQLAlchemy | 2.0+ | MIT | Mike Bayer |
| Pydantic | 2.x | MIT | Samuel Colvin |
| Uvicorn | — | BSD-3-Clause | Encode OSS |
| python-jose | — | MIT | Michael Davis |
| passlib | — | BSD | Eli Collins |
| psycopg2 | — | LGPL-3.0 | Federico Di Gregorio, Daniele Varrazzo |
| pandas | — | BSD-3-Clause | Pandas Development Team |
| numpy | — | BSD-3-Clause | NumPy Developers |
| scikit-learn | — | BSD-3-Clause | Scikit-learn Developers |
| XGBoost | — | Apache-2.0 | DMLC/XGBoost Contributors |
| joblib | — | BSD-3-Clause | Joblib Contributors |
| redis | — | MIT | Redis Labs |
| rq | — | BSD-2-Clause | Selwin Ong |
| sendgrid | — | MIT | Twilio / SendGrid |
| bcrypt | — | Apache-2.0 | OpenBSD Contributors |
| APScheduler | — | MIT | Alex Grönholm |

### ML (Python)

| Biblioteca | Versión | Licencia | Autores / Mantenedores |
|-----------|---------|---------|----------------------|
| scikit-learn | — | BSD-3-Clause | Scikit-learn Developers |
| XGBoost | — | Apache-2.0 | DMLC/XGBoost Contributors |
| pandas | — | BSD-3-Clause | Pandas Development Team |
| numpy | — | BSD-3-Clause | NumPy Developers |
| matplotlib | — | PSF / BSD-compatible | Matplotlib Development Team |
| seaborn | — | BSD-3-Clause | Michael Waskom |
| plotly | — | MIT | Plotly Technologies Inc. |
| joblib | — | BSD-3-Clause | Joblib Contributors |
| tqdm | — | MIT / MPLv2 | tqdm Developers |
| feature-engine | — | BSD-3-Clause | Soledad Galli |
| Jupyter | — | BSD-3-Clause | Project Jupyter Contributors |

### Scrapping (Python)

| Biblioteca | Versión | Licencia | Autores / Mantenedores |
|-----------|---------|---------|----------------------|
| requests | — | Apache-2.0 | Kenneth Reitz |
| BeautifulSoup4 | — | MIT | Leonard Richardson |
| lxml | — | BSD-3-Clause | lxml Dev Team |
| Selenium | — | Apache-2.0 | Software Freedom Conservancy |
| webdriver-manager | — | Apache-2.0 | Sergei Pirogov |
| APScheduler | — | MIT | Alex Grönholm |
| psycopg2 | — | LGPL-3.0 | Federico Di Gregorio, Daniele Varrazzo |
| SQLAlchemy | — | MIT | Mike Bayer |

### Frontend (JavaScript / TypeScript)

| Biblioteca | Versión | Licencia | Autores / Mantenedores |
|-----------|---------|---------|----------------------|
| React | 19.1.1 | MIT | Meta Platforms, Inc. |
| React DOM | 19.1.1 | MIT | Meta Platforms, Inc. |
| TypeScript | ~5.9.3 | Apache-2.0 | Microsoft Corporation |
| Vite | 7.1.7 | MIT | Evan You / Vite Contributors |
| React Router | 7.9.4 | MIT | Remix Software |
| Zustand | 5.0.8 | MIT | Paul Henschel, Daishi Kato |
| Tailwind CSS | 3.4.13 | MIT | Tailwind Labs |
| Radix UI | — | MIT | WorkOS |
| shadcn/ui | — | MIT | shadcn |
| lucide-react | — | ISC | Lucide Contributors |
| ESLint | — | MIT | OpenJS Foundation |

---

## 3. Fuente de Datos

Los datos deportivos utilizados en este proyecto provienen de:

**ESPN (Entertainment and Sports Programming Network)**
- Sitio web: https://www.espn.com
- Propietario: The Walt Disney Company
- Tipo de datos: Estadísticas de partidos NBA, estadísticas de jugadores y
  equipos, reportes de lesiones, clasificaciones de temporada.

**Condiciones de uso de los datos**:
Los datos de ESPN son de carácter público y se acceden a través de sus
páginas web mediante técnicas de web scraping con fines estrictamente
académicos y no comerciales, en concordancia con el propósito investigativo
de este Trabajo de Grado. No se redistribuyen los datos en bruto ni se
utilizan con fines de lucro.

Este proyecto no está afiliado, patrocinado ni respaldado por ESPN ni por
The Walt Disney Company.

**NBA (National Basketball Association)**
- Las estadísticas y resultados de partidos de la NBA son propiedad de la
  National Basketball Association.
- Su uso en este proyecto es exclusivamente académico.

---

## 4. Plataformas de Infraestructura

| Plataforma | Uso | Términos |
|-----------|-----|---------|
| Neon | Base de datos PostgreSQL cloud | https://neon.tech/terms |
| Render | Hosting del Backend | https://render.com/terms |
| Vercel | Hosting del Frontend | https://vercel.com/legal/terms |
| SendGrid (Twilio) | Servicio de email | https://www.twilio.com/legal/tos |

---

## 5. Descargo de Responsabilidad

Este sistema fue desarrollado con propósitos **exclusivamente académicos y
educativos** como requisito para la obtención del título de pregrado en la
Universidad Manuela Beltrán.

- **No involucra dinero real**: Todos los créditos utilizados en el sistema
  de apuestas son virtuales y no tienen valor monetario.
- **No constituye asesoramiento**: Las predicciones generadas por los modelos
  de machine learning son probabilísticas y no representan asesoramiento
  financiero ni de apuestas.
- **No fomenta el juego patológico**: El sistema es una demostración técnica
  del uso de machine learning aplicado a datos deportivos.

---

## 6. Derechos Morales

De conformidad con el Artículo 30 de la Ley 23 de 1982 (Colombia), los
autores conservan en todo momento sus derechos morales sobre esta obra,
los cuales son inalienables, irrenunciables e imprescriptibles:

- Derecho de paternidad: reconocimiento de Irving Rios Ramirez y Jhon Edison
  Montaño Parra como autores de la obra.
- Derecho de integridad: la obra no puede ser modificada de forma que atente
  contra el honor o reputación de los autores.
- Derecho de divulgación: los autores decidieron el modo y momento de
  publicación de este trabajo.

---

*Para consultas sobre licenciamiento o uso de este trabajo, contactar a los
autores a través de la Universidad Manuela Beltrán.*
