# DOC-001: Project Solaris Constitution v1.0

Project Solaris: Physics-Informed Multi-Modal Solar Flare Early Warning System

Prepared for: Bharatiya Antariksh Hackathon 2026, ISRO Problem Statement #15  
Document status: Canonical foundation document  
Version: 1.0  
Date: 2026-06-16  

## Document Authority

This Constitution is the master source of truth for Project Solaris. It defines the mission, scientific framing, system architecture, engineering philosophy, evaluation approach, product direction, execution model, and defense posture for the project. Every later document in the Project Solaris documentation hierarchy should derive from this Constitution, refine it for a specific purpose, or record a decision made against it.

The purpose of this document is not to act as a short proposal. It is not a pitch deck, dashboard specification, or code plan. It is the permanent foundation from which a new team should be able to reconstruct the project with scientific continuity and strategic discipline. When tradeoffs emerge, this Constitution should be treated as the reference that keeps the project aligned with its central thesis: Project Solaris is a physics-informed, explainable, multimodal solar flare early warning system that uses the dual-band X-ray opportunity represented by Aditya-L1 to move flare prediction from black-box classification toward operational space-weather decision support.

The project must resist the temptation to become an ordinary machine learning classifier with a polished interface. The technical work matters, but the reason it matters is larger than model performance. Project Solaris exists to demonstrate how Indian space-weather capability can be strengthened by combining mission-specific data, physically meaningful features, uncertainty-aware forecasting, explainable reasoning, and operationally useful warning products. The hackathon is the first milestone. The long-term ambition is a credible research and engineering pathway toward an ISRO-aligned space-weather platform.

## Part I: Mission

Project Solaris is built around a mission problem: the Sun can produce eruptive events that affect satellites, communications, navigation, electrical infrastructure, astronauts, and future human activity beyond low Earth orbit. Solar flares are among the most visible and rapidly evolving expressions of solar activity. They release intense radiation across the electromagnetic spectrum, including soft X-rays and hard X-rays, and they are often associated with broader space-weather hazards such as coronal mass ejections and solar energetic particle events. A useful warning system must therefore do more than predict a label. It must help operators understand risk, urgency, confidence, and physical basis.

The immediate competition context is Bharatiya Antariksh Hackathon 2026, ISRO Problem Statement #15: forecasting and/or nowcasting of solar flares using combined soft and hard X-ray data from Aditya-L1. The project should satisfy the hackathon requirement, but it should not be shaped as a disposable prototype. The correct design posture is to build an architecture and documentation system that can evolve after the event into a research project, an operational decision-support system, a publication pathway, a startup or spinoff concept, and a wider space-weather platform. Hackathon constraints should determine scope and sequencing, not ambition.

The mission is to create an early warning system that answers five operational questions: Will a flare occur? How confident are we? Why does the system believe this? Is the Sun behaving unusually? What might the downstream radiation or mission risk be? This framing deliberately expands the project beyond a binary flare classifier. A model that emits only a probability can be technically impressive yet operationally weak. A mission operator needs an explanation, a confidence band, an anomaly signal, a time horizon, and a sense of possible consequence.

The project must keep ISRO impact at the center. The strongest argument for Project Solaris is not that a Dual-Branch Cross-Attention GRU is novel in isolation. The strongest argument is that Aditya-L1 can observe the Sun from the L1 point using Indian payloads, including instruments relevant to soft and hard X-ray science, and that these observations create an opportunity for India to develop mission-specific space-weather intelligence. Project Solaris should be presented as a system that turns scientific measurement into actionable mission awareness.

The project mission has three layers. The first is the hackathon layer: build a convincing, working, explainable demonstration using available proxy data. The second is the research layer: show that thermal and non-thermal X-ray dynamics can be fused in a physics-aware model that is more credible than black-box time-series classification. The third is the operational layer: define a path from model predictions to dashboarded warning products that could eventually support satellite operations, human spaceflight planning, and national space-weather resilience.

Winning the hackathon is important, but it is not the only success condition. A narrow project can win attention and still be forgotten. Project Solaris should instead be constructed so that every artifact demonstrates continuity: the Constitution defines the thesis, the decision log records tradeoffs, the research documents defend the science, the system documents specify the architecture, the dashboard demonstrates operational usability, and the technical defense explains why the approach is credible. If the team maintains that continuity, even a limited first implementation can feel like the visible surface of a serious system.

## Part II: Domain Understanding

Solar flares are sudden releases of magnetic energy in the solar atmosphere. They appear across many wavelengths, but X-rays are especially important because they respond strongly to energetic plasma processes. Soft X-rays are associated with hot thermal plasma, while hard X-rays are associated more directly with accelerated non-thermal electrons and impulsive energy release. This difference is central to Project Solaris. The project is not merely using two data streams because two streams are available. It is using them because soft and hard X-ray observations represent related but distinct physical views of flare evolution.

Operational flare forecasting and nowcasting are difficult because the Sun is nonlinear, data are noisy, the most dangerous events are rare, and the lead-time requirement conflicts with the uncertainty of early signals. A classifier trained to recognize flare and non-flare intervals can learn useful correlations, but it can also overfit calendar effects, background flux states, instrument artifacts, or event selection biases. A system intended for operational trust must therefore include physically interpretable features, uncertainty estimation, anomaly detection, and transparent reasoning. Accuracy alone is insufficient.

Flare prediction can be divided into several temporal modes. Long-range forecasting asks whether an active region may flare over hours or days. Short-range forecasting asks whether a flare is likely within a defined upcoming window. Nowcasting identifies whether an event is already beginning or imminent based on rapidly changing sensor signals. Project Solaris should focus its hackathon implementation on short-range forecasting and nowcasting using time-series X-ray behavior. This focus is aligned with the available data and with the problem statement. The project should avoid overclaiming that it solves all forms of flare forecasting.

The system must recognize flare classes, because operational interpretation depends on event magnitude. The NOAA/SWPC flare classification system uses peak soft X-ray flux in the 1-8 Angstrom band and categorizes events into A, B, C, M, and X classes, with each class representing a factor-of-ten increase in peak flux. This standard is not only a labeling convenience; it is part of how space-weather stakeholders discuss event severity. Project Solaris should use this convention when mapping model outputs to user-facing risk levels and when reporting evaluation results.

The hard part is not only detecting large events after their signal is obvious. The project should be oriented toward precursors and early warning. Several classes of features can be valuable: the absolute soft X-ray flux, the absolute hard X-ray flux, the hardness ratio between hard and soft X-ray channels, the derivative of soft X-ray flux, integrated hard X-ray energy, waiting time since the previous event, rolling statistics, slopes, volatility, and reconstruction error from a quiet-Sun anomaly model. These features convert raw time series into physically meaningful signals.

The Neupert effect provides the most important physics-informed anchor. In simplified terms, the time derivative of soft X-ray emission often resembles the hard X-ray emission during flare evolution. This relationship is not an exact law for every event, and the project must not pretend that it is. But it is a scientifically meaningful connection between non-thermal electron acceleration and the buildup of thermal plasma emission. Project Solaris should use this relationship as a soft constraint, not a brittle rule. The model should be encouraged to respect the relationship where appropriate while retaining the flexibility to handle real solar variability.

Space weather systems also need to handle rarity and imbalance. Major flares are rare compared with quiet or weakly active intervals. A naive model can achieve high accuracy by predicting no event most of the time. Project Solaris must therefore evaluate with metrics that reflect operational usefulness, including recall for meaningful flare classes, false alarm rate, precision, lead time, calibration, and event-based scoring. The dashboard should not hide these tradeoffs. It should communicate that warning systems must balance missed events against false alarms, and that different mission contexts may prefer different thresholds.

The domain also requires humility. Solar activity is complex, instrument behavior matters, proxy datasets are imperfect, and the hackathon system will not be a final operational service. The Constitution therefore defines a disciplined scientific posture: use available data honestly, document assumptions, separate current implementation from future Aditya-L1 deployment, and make every claim traceable to a model output, a feature, or a physical argument.

## Part III: Aditya-L1 Context

Aditya-L1 is India's first dedicated solar mission and is positioned around the Sun-Earth L1 region to observe the Sun with reduced occultation constraints compared with low Earth orbit. For Project Solaris, the strategic importance of Aditya-L1 is not simply national pride. The mission creates a data context in which India can build sovereign, mission-specific space-weather intelligence. A system designed around Aditya-L1 payload logic is more aligned with ISRO's future needs than a generic classifier trained only to reproduce public catalogs.

The project specifically centers on the opportunity to combine soft and hard X-ray measurements. In the target future configuration, SoLEXS is treated as the soft X-ray source and HEL1OS as the hard X-ray source. The Solar Low Energy X-ray Spectrometer is relevant for soft X-ray flare behavior, while the High Energy L1 Orbiting X-ray Spectrometer is relevant for higher-energy flare emission. This pairing supports the central thesis: thermal and non-thermal flare signatures should be modeled together rather than in isolation.

Aditya-L1's L1 vantage point strengthens the operational narrative. Observations from L1 can support continuous solar monitoring and can be naturally connected to space-weather operations. Project Solaris should communicate that the system is designed as a bridge between payload measurements and mission decisions. The model is not the product by itself. The product is a warning workflow: measurements enter, features are computed, the multimodal model estimates risk, uncertainty is calculated, explanation layers identify the basis of the warning, anomaly detection supplies an independent signal, and the dashboard communicates what an operator should pay attention to.

The hackathon implementation cannot assume full operational Aditya-L1 data availability. The correct strategy is to use scientifically defensible proxy datasets. GOES XRS can serve as a soft X-ray proxy because GOES X-ray Sensor data are a long-standing basis for solar X-ray monitoring and flare classification. RHESSI can serve as a hard X-ray proxy for historical solar flare behavior, and Fermi GBM can provide additional hard X-ray and gamma-ray context. NOAA flare catalogs can provide event labels and timing. These proxies should be documented as proxies, not as exact substitutes for Aditya-L1 instruments.

This distinction is critical. The Constitution defines two data identities: the hackathon data identity and the future mission data identity. In the hackathon identity, the project demonstrates the architecture using GOES, RHESSI, Fermi GBM, and NOAA labels. In the future mission identity, the same architecture ingests SoLEXS and HEL1OS data. The project should show that the architecture is designed for Aditya-L1 even when the first working prototype uses public historical data.

Aditya-L1 context also shapes the explanation strategy. A system built for ISRO should not merely display generic feature attributions. It should explain model behavior in terms of the mission's sensor logic: hard X-ray strengthening, soft X-ray derivative changes, spectral hardening, anomalous departure from quiet-Sun behavior, elevated integrated non-thermal energy, and time since prior event. These are concepts a scientific or mission stakeholder can interrogate. If a judge asks why the model predicts elevated risk, the answer should be grounded in the interaction between payload-relevant measurements and solar physics.

The project should cite official mission and instrument sources in supporting documents and presentations. The Constitution records the framing, while later documents should expand the payload analysis and data architecture. The official Aditya-L1 mission page from ISRO, NOAA/SWPC documentation on GOES X-ray monitoring and flare classification, NASA mission material on RHESSI, and NASA/Fermi GBM material should be treated as baseline reference sources for external factual claims.

## Part IV: Problem Definition

The formal problem is to forecast and/or nowcast solar flares using combined soft and hard X-ray data in a way that is scientifically credible, operationally useful, explainable, and feasible within hackathon constraints. The project should produce an early warning system rather than a standalone model. The input is a multivariate time sequence derived from soft and hard X-ray observations and engineered physical features. The output is a structured warning product that includes flare probability, expected risk class or severity band, time-to-flare estimate where feasible, confidence or uncertainty interval, anomaly index, explanatory attributions, and optional downstream radiation-risk context.

The problem is not solved by a binary label alone. A yes-or-no forecast ignores the fact that operational decisions depend on confidence, consequence, and timing. For example, a low-confidence warning for a weak C-class event should not be treated the same as a high-confidence warning for an M-class or X-class event. Similarly, an anomalous pre-flare signal may deserve attention even if the classifier probability has not crossed a hard threshold. Project Solaris must preserve these distinctions in both the model outputs and the dashboard.

The core prediction task should be defined over fixed time windows. A model ingests a lookback window of recent X-ray behavior and predicts whether a flare of a specified class threshold will occur within a forecast horizon. Multiple horizons can be supported, such as near-nowcasting and short-term windows, but the first implementation should keep the scope controlled. The Constitution recommends beginning with a single primary horizon and then extending to multiple horizons if data preparation and evaluation are stable. The system may also include a severity head that estimates flare class band.

The anomaly detection task is separate. A GRU autoencoder should be trained primarily on quiet-Sun or non-flaring intervals to reconstruct normal behavior. When the reconstruction error rises, it produces an anomaly index from 0 to 100. This signal should not be treated as identical to flare probability. It is an independent warning channel that says the current solar behavior differs from learned quiet or normal dynamics. The value of this design is operational: a classifier may be uncertain, but an anomaly signal can still alert the operator that the system is seeing unusual conditions.

The physics-informed task is also separate but connected. The system should compute a Neupert-consistency term comparing hard X-ray behavior with the derivative of soft X-ray behavior after appropriate smoothing, normalization, lag handling, and event-window alignment. This term can be used during training as an auxiliary loss. It can also be shown during explanation as a physics-consistency diagnostic. The project should be careful to state that the Neupert relationship is an inductive bias, not a universal truth imposed rigidly on every sample.

The project must manage data constraints transparently. Public datasets differ in cadence, energy bands, coverage, instrument response, data gaps, and event definitions. The problem definition therefore includes data harmonization as a first-class challenge. Time alignment, resampling, gap handling, normalization, background subtraction, event-window construction, negative sampling, and train-test temporal separation are not implementation details to be hidden. They are part of the scientific validity of the system.

The intended users are not generic consumers. The primary audience is a space-weather analyst, mission operations reviewer, ISRO evaluator, or technical judge. Secondary audiences include researchers, satellite operators, human spaceflight planners, and future product stakeholders. Because the primary user is technical but time-constrained, the interface must be dense, legible, and decision-oriented. It should not feel like a marketing dashboard. It should feel like a mission control tool that highlights what changed, why risk moved, and how much confidence the system has.

The success criterion is not maximum benchmark performance at any cost. The success criterion is a defensible system that improves the decision process. The model should be accurate enough to be credible, but it should also be explainable enough to be trusted, uncertainty-aware enough to avoid false precision, and mission-oriented enough to show why it helps ISRO.

## Part V: Research Review

Existing solar flare forecasting work spans statistical methods, machine learning classifiers, deep temporal models, active-region magnetic feature analysis, image-based approaches, and operational warning systems. Many modern projects use magnetogram-derived features, active-region histories, or soft X-ray time series. These approaches can be valuable, but they leave an opportunity for Project Solaris: a focused dual-band X-ray system that learns the relationship between thermal and non-thermal flare dynamics and connects that relationship to an operational warning interface.

The expected hackathon field will likely contain LSTM models, Transformer models, binary classifiers, and dashboards. These are natural choices because time-series prediction and visual display are intuitive responses to the problem statement. Project Solaris should not compete only on that axis. A generic Transformer with a flare probability output may be strong technically, but it risks becoming indistinguishable from other submissions. The differentiator must be the whole thesis: physics-informed multimodal fusion, uncertainty quantification, anomaly detection, explainability, and mission impact.

The research review supports the chosen architecture. Transformers are powerful but can be implementation-heavy, data-hungry, and harder to explain cleanly under hackathon time pressure. Mamba-style sequence models and temporal graph approaches may be interesting, but they introduce complexity that may not translate into a stronger demonstration. A Dual-Branch Cross-Attention GRU offers a disciplined balance. GRUs are efficient for sequential data, easier to train on modest datasets, and familiar enough to defend. Separate branches allow soft and hard X-ray sequences to be encoded independently. Cross-attention allows the model to learn interactions between modalities rather than merely concatenate them.

The cross-attention mechanism is important because the project thesis is interactional. The system should discover when hard X-ray behavior modifies the interpretation of soft X-ray behavior and when soft X-ray evolution changes the meaning of hard X-ray bursts. Simple concatenation treats the modalities as parallel columns. Cross-attention gives the architecture a way to express relationships across time and modality. This can be visualized as attention heatmaps, supporting the explainability goal.

Physics-informed learning is a major research differentiator. Many machine learning systems learn from labels without being constrained by domain knowledge. Project Solaris should instead incorporate the Neupert effect through feature design and loss design. The prediction loss should capture the supervised flare objective. The Neupert loss should penalize mismatch between normalized hard X-ray behavior and the derivative of soft X-ray behavior in relevant windows. The total loss can be expressed as prediction loss plus lambda times Neupert loss, with lambda selected through validation. This does not guarantee better performance, but it improves scientific credibility and gives the model a more meaningful inductive bias.

Uncertainty quantification must be treated as mandatory. A model that produces a single probability is often overconfident, especially under distribution shift. Monte Carlo Dropout is preferred because it is simple, feasible, and explainable within the hackathon timeline. At inference, dropout remains active across multiple stochastic passes, producing a distribution of predictions. The mean can be reported as risk probability, while variance or percentile bands can be reported as uncertainty. This supports operational language such as "high risk, low uncertainty" or "moderate risk, high uncertainty."

Explainability should be operational, not decorative. SHAP values, attention heatmaps, feature importance, temporal attribution, and physics-consistency signals should answer why the warning is elevated. A chart that only looks sophisticated does not help if it cannot explain the decision. The explanations should be connected to named features: hardness ratio increased, soft X-ray derivative steepened, integrated hard X-ray energy rose, the sequence looked anomalous compared with quiet-Sun behavior, or attention concentrated on a specific interval before the predicted event.

The research review also supports a future SEP extension. Solar energetic particle risk is not the same as flare prediction, and the first implementation should not overclaim SEP forecasting performance. However, the narrative matters because human spaceflight, Gaganyaan, Bharatiya Antariksha Station, satellite operations, and radiation protection make particle risk operationally meaningful. Project Solaris should include a lightweight SEP-risk module or conceptual extension that uses flare severity, hard X-ray behavior, event history, and uncertainty to produce a preliminary radiation-risk indicator. This should be framed as an extension, not as a fully validated SEP forecast.

The research posture should be honest and ambitious at the same time. The first system will use proxies, simplified losses, and constrained horizons. That is acceptable if the documentation explains why the architecture is designed to evolve into a mission-aligned platform. The credibility of Project Solaris will come from the coherence between the science, the model, the interface, and the defense narrative.

## Part VI: Solution Thesis

The solution thesis is that the interaction between soft X-ray and hard X-ray emissions contains exploitable precursor information for flare nowcasting and short-term forecasting, and that embedding solar-physics structure into machine learning can improve scientific credibility, interpretability, and operational trust. This thesis must appear in every major artifact. It is the difference between Project Solaris and a generic flare classifier.

Soft X-rays and hard X-rays should be treated as complementary evidence streams. Soft X-rays describe the evolving thermal response of hot plasma. Hard X-rays provide insight into impulsive energetic processes and accelerated particles. A flare warning system that uses only one of these streams may miss part of the physical story. Combining both streams gives the model a chance to learn whether a rising thermal signal is accompanied by non-thermal activity, whether hard X-ray bursts precede or align with soft X-ray changes, and whether spectral hardening indicates a transition toward higher risk.

The model architecture operationalizes this thesis. The soft branch encodes soft X-ray flux, derivative, rolling statistics, and related features. The hard branch encodes hard X-ray flux, integrated hard X-ray energy, hardness behavior, and hard-band temporal statistics. Cross-attention fuses the branches so each modality can influence the interpretation of the other. A physics constraint layer introduces Neupert-aware training pressure. A forecasting head outputs risk and severity. An uncertainty layer estimates confidence. An explainability layer exposes attribution and attention. A separate autoencoder generates anomaly index. The dashboard turns these outputs into a mission-control display.

The thesis has a strong judging advantage because it shifts the conversation from model type to mission value. If a judge asks why the project matters, the answer is not "because GRUs are good." The answer is that Aditya-L1 provides an opportunity to combine Indian solar observations into an early warning workflow that is physically informed, explainable, uncertainty-aware, and operationally relevant. The architecture exists to serve that mission.

The thesis also defines what the project should not do. It should not become architecture obsessed. It should not spend excessive time comparing fashionable sequence models if the core demonstration remains weak. It should not present a black-box probability as sufficient. It should not hide uncertainty. It should not claim to replace operational centers. It should not pretend proxy data are identical to Aditya-L1 data. It should not overstate SEP forecasting. It should not produce isolated documents that contradict each other.

The solution must be modular. Each component should have a clear role and a clear failure mode. The data layer gathers and harmonizes time series. The feature layer produces physically meaningful variables. The soft and hard encoders model temporal behavior within each modality. The fusion layer learns cross-modal relationships. The physics layer regularizes the learned representation. The forecast head estimates flare risk. The uncertainty layer prevents false precision. The anomaly module flags unusual behavior. The explanation module communicates why. The dashboard converts model output into human decision support.

This modularity is not bureaucracy. It is what allows the project to evolve. During the hackathon, several modules may be simplified. Later, the data layer can switch from proxy datasets to Aditya-L1 feeds, the model can be retrained, the physics loss can be refined, the SEP module can be validated, and the dashboard can be connected to operational workflows. The Constitution therefore defines the solution as a platform pattern, not a single notebook.

The thesis should be evaluated through both scientific and product lenses. Scientifically, the model should demonstrate that multimodal features and physics-aware loss improve or at least defensibly support forecasting performance and explanation quality. Product-wise, the dashboard should show that the outputs can guide decisions better than a single label. The ideal demo moment is not merely a high probability appearing on screen. It is a situation where the system shows rising risk, provides confidence, highlights the physical drivers, detects unusual solar behavior, and frames mission relevance.

## Part VII: System Design

The system design follows a layered architecture: data layer, feature engineering, soft X-ray encoder, hard X-ray encoder, cross-attention fusion, physics constraint layer, forecasting head, uncertainty layer, explainability layer, anomaly detection module, SEP extension, and mission dashboard. Each layer should be independently understandable and testable. The architecture should be documented visually in DOC-301 and technically in DOC-302 through DOC-304, but the Constitution defines the permanent design intent.

The data layer ingests time-stamped observations from soft X-ray and hard X-ray sources. In the hackathon implementation, GOES XRS is the primary soft X-ray proxy. RHESSI and Fermi GBM are hard X-ray or higher-energy proxies depending on availability and preprocessing feasibility. NOAA flare catalogs provide labels, event timing, and class information. In the future mission implementation, SoLEXS and HEL1OS replace or complement these proxies. The data layer must preserve provenance, cadence, instrument identity, preprocessing choices, and gaps.

The feature engineering layer converts raw time series into model-ready inputs. Mandatory features include soft X-ray flux, hard X-ray flux, hardness ratio, soft X-ray derivative, integrated hard X-ray energy, waiting-time statistics, and rolling statistical features such as mean, variance, slope, and volatility. These features should be computed over consistent windows and normalized without leaking future information. The hardness ratio should be handled carefully to avoid instability when denominators are small. Derivatives should be smoothed enough to reduce noise while preserving rapid energy-release behavior.

The soft X-ray encoder is a GRU-based temporal branch. It processes soft-band features and learns patterns such as background elevation, rising flux, derivative acceleration, and thermal response shape. The hard X-ray encoder is a parallel GRU branch that processes hard-band features and learns impulsive bursts, cumulative energy behavior, and spectral hardening context. Separate branches preserve modality identity before fusion. This is preferable to immediate concatenation because it lets each modality develop its own temporal representation.

The cross-attention fusion layer allows the branches to interact. The soft representation can attend to hard X-ray time steps, and the hard representation can attend to soft X-ray time steps. The result is a fused representation that captures cross-modal timing and relevance. This layer is also valuable for explainability because attention weights can be visualized as heatmaps. The team should avoid overclaiming that attention is always explanation, but attention maps can still provide useful inspection when paired with other attribution methods.

The physics constraint layer introduces Neupert-aware regularization. During training, the model should compute a loss term that measures discrepancy between normalized hard X-ray behavior and the derivative of soft X-ray behavior across appropriate windows. Practical implementation details matter: signals may need smoothing, lag tolerance, robust normalization, and masking for data gaps. The loss weight lambda should be validated, not chosen arbitrarily. A small lambda may provide gentle guidance; an excessive lambda may harm performance by forcing the model to obey an imperfect relationship.

The forecasting head produces flare risk. The simplest first version should output probability for a defined forecast horizon and threshold, such as event above a chosen class within the next interval. A more complete version can output multiple heads: binary risk, severity class, and time-to-flare estimate. The Constitution recommends beginning with a robust primary head and adding secondary heads only after the data pipeline and evaluation are stable.

The uncertainty layer uses Monte Carlo Dropout. At inference, the same input is passed through the model multiple times with dropout enabled. The resulting prediction distribution gives mean risk, variance, and confidence bands. The dashboard should communicate this directly. A high mean with high variance should feel different from a high mean with low variance. Threshold decisions can use both probability and uncertainty, especially for mission-critical alerts.

The explainability layer includes SHAP or equivalent feature attribution, attention visualization, temporal attribution, and physics diagnostics. The goal is not to overwhelm the user with every method at once. The dashboard should surface the most decision-useful explanations: top contributing features, influential time windows, attention between modalities, and whether the Neupert-consistency signal supports or conflicts with the warning.

The anomaly detection module is a GRU autoencoder trained separately on quiet or normal intervals. Its reconstruction error is mapped to an anomaly index from 0 to 100. This module should not be trained to predict flares directly. Its purpose is to provide an independent measure of unusual solar behavior. A rising anomaly index can support early warning, draw attention to rare dynamics, or explain why the system is cautious even when forecast probability is moderate.

The SEP extension should remain lightweight in version 1.0. It may produce a conceptual radiation-risk indicator based on flare probability, expected severity, hard X-ray intensity, event history, and uncertainty. It should be framed as a future extension relevant to human spaceflight and radiation protection. A full SEP forecasting model requires additional particle data and validation, which should be documented as future work.

The dashboard should be built in Streamlit with Plotly visualizations for the hackathon phase. Required components are live or replayable soft X-ray plot, hard X-ray plot, flare risk gauge, time-to-flare estimate, confidence interval, anomaly index, SHAP or attribution view, and attention heatmap. Optional components include a 3D time-energy spectrogram after core functionality works. The interface should feel like mission control: clear, technical, information-dense, and calm. It should not be a landing page.

## Part VIII: Engineering

The engineering philosophy is to build a reproducible, modular, scientifically honest system. Every data transformation should be traceable. Every model output should be reproducible from a specific version of code, data, configuration, and trained weights. Every result in the presentation should be backed by an experiment record. Hackathon speed is not an excuse for undocumented behavior, because the project aims to be more than a hackathon artifact.

The repository should be organized around stable responsibilities. A recommended structure is `data/` for local or downloaded data references, `src/solaris/` for package code, `notebooks/` for exploration, `configs/` for experiment settings, `models/` for trained artifacts or references, `docs/` for documentation, `reports/` for generated analysis, and `app/` for dashboard code. The first actual code implementation may simplify this structure, but the names and boundaries should remain consistent enough for a new contributor to understand where work belongs.

Data engineering must be treated as scientific infrastructure. The pipeline should ingest raw files, standardize timestamps, resample to a chosen cadence, align modalities, label forecast windows, compute features, split data temporally, and persist processed datasets. The team should avoid random splits that leak future behavior into training. Solar time series have temporal dependencies, and event-based evaluation can be distorted by leakage. Splits should respect chronological order or event grouping.

Feature computation should be deterministic and versioned. If the hardness ratio formula changes, if derivative smoothing changes, or if waiting-time definitions change, the experiment should record it. The same applies to label windows and event thresholds. Without this discipline, model comparisons become meaningless. A good hackathon defense can acknowledge that the first system is constrained while showing that the engineering practices support future research-grade iteration.

Model training should be configuration-driven. The configuration should specify lookback window, forecast horizon, flare threshold, feature list, normalization method, model dimensions, dropout rate, physics-loss weight, optimizer settings, batch size, and random seed. The team should log metrics, calibration, confusion matrices, and selected visual examples. If time allows, experiment tracking should be added. If not, structured run outputs should still be saved in a consistent folder.

The model stack should favor reliability over novelty. PyTorch is a suitable implementation framework for the Dual-Branch Cross-Attention GRU and GRU autoencoder. Scikit-learn can support preprocessing, metrics, and baseline models. Pandas and NumPy can manage tabular time-series transformations. Streamlit and Plotly can deliver the dashboard. SHAP can support attribution if integration is feasible; if not, permutation importance and gradient-based temporal attribution can be used as practical fallbacks with clear documentation.

Baselines are mandatory. Project Solaris should compare the proposed model against simple baselines such as persistence, threshold rules, logistic regression on engineered features, random forest or gradient boosting, and a single-modality GRU. A project that only presents the advanced model cannot prove that complexity helped. Baselines also improve defense because they show the team understands scientific comparison.

Testing should cover the data pipeline, feature calculations, label generation, and model-output shapes. Unit tests should verify that derivative features do not use future data, hardness ratios handle zeros safely, rolling windows align correctly, and label windows are computed as intended. Integration tests should run a small sample through preprocessing, training or inference, and dashboard-ready output generation. The goal is not exhaustive enterprise coverage during a hackathon. The goal is to catch errors that would undermine scientific credibility.

The dashboard engineering should separate inference from display. A dashboard should consume prepared prediction records or call a stable inference function. It should not contain hidden preprocessing logic that differs from training. This separation makes the system easier to test and easier to explain. It also allows the demo to support replay mode, where historical intervals are played as if live, which is often the best way to demonstrate a space-weather warning system with public data.

Documentation engineering is part of the system. DOC-001 is the Constitution. DOC-002 is the decision log. DOC-101 through DOC-503 derive from the Constitution. The documentation hierarchy prevents fragmentation. When an architectural choice changes, the decision log records why. When the dashboard is specified, it refers to the system design. When the defense handbook is written, it draws from the thesis, limitations, and evidence already recorded here.

Security and operational discipline should be considered even if the first version is local. Data provenance, model versioning, reproducible environment setup, and transparent limitations are all part of trust. If the project later evolves toward operational use, it will need stronger controls around data feeds, alert thresholds, audit logs, access, reliability, and fallback behavior. The Constitution plants those requirements now so the project does not grow in the wrong direction.

## Part IX: Evaluation

Evaluation must measure both predictive performance and operational usefulness. A model can look strong on aggregate metrics and still be poor for warning operations. Project Solaris should therefore evaluate classification accuracy, event recall, false alarm behavior, lead time, calibration, uncertainty quality, explanation usefulness, and anomaly signal behavior. The evaluation should be honest about what is validated in the hackathon version and what remains future work.

The first class of metrics concerns event prediction. Depending on the selected task, the project should report precision, recall, F1-score, ROC-AUC, PR-AUC, confusion matrix, and class-specific performance for relevant flare thresholds. Because flaring events are imbalanced, PR-AUC and recall at controlled false alarm rates may be more informative than plain accuracy. If severity classification is included, the team should report class-wise performance and avoid hiding weak performance on rare high-class events.

The second class of metrics concerns lead time. A warning system should be judged on whether it provides useful notice before or near event onset. For each detected event, the evaluation should estimate how early the model crosses a warning threshold relative to the catalog onset time. This should be summarized as median lead time, distribution of lead times, and examples. A warning after the event is obvious may still be useful for nowcasting, but it should not be represented as long-range forecasting.

The third class concerns false alarms and missed events. Operational systems must trade off sensitivity and alert fatigue. Project Solaris should show how the threshold affects recall and false alarm rate. A mission dashboard may allow threshold modes such as conservative, balanced, and sensitive. These modes should be tied to the model's calibration and uncertainty rather than arbitrary visual settings.

The fourth class concerns calibration and uncertainty. If the model says 80 percent risk across many samples, approximately 80 percent of those cases should correspond to the event definition over a well-calibrated set. Calibration curves, reliability diagrams, Brier score, and expected calibration error can support this analysis. Monte Carlo Dropout variance should be evaluated qualitatively and quantitatively. High uncertainty should correlate with ambiguous cases, out-of-distribution behavior, data gaps, or conflicting signals.

The fifth class concerns the physics-informed component. The team should evaluate whether the Neupert loss changes performance, explanation, or robustness. This can be done through ablation: train the same architecture with and without the physics loss, compare predictive metrics, inspect attention and attribution behavior, and examine physics-consistency diagnostics on selected events. The outcome may be nuanced. If the physics loss improves interpretability but only modestly changes accuracy, that can still support the project's thesis when presented honestly.

The sixth class concerns multimodal value. The project must show why using both soft and hard X-ray data matters. Ablations should compare soft-only, hard-only, concatenated multimodal, and cross-attention multimodal variants if time allows. Even a limited ablation can strengthen the defense. The key question is whether cross-modal interaction contributes useful signal beyond either modality alone.

The seventh class concerns anomaly detection. The GRU autoencoder should be evaluated on quiet intervals, known flaring intervals, and selected anomalous periods. Metrics may include reconstruction error distributions, threshold behavior, and case studies where anomaly index rises before or during events. The team should avoid claiming that the anomaly index is a fully validated flare predictor unless evaluation supports it. It is an independent signal, not a replacement for supervised forecasting.

The eighth class concerns explanation quality. Explanations are hard to score automatically, but they can be evaluated through consistency and plausibility. If the system predicts high risk, do the top features and time windows align with actual changes in X-ray behavior? Do attention maps concentrate on meaningful intervals? Do SHAP or attribution values identify hardness ratio, derivative, integrated hard X-ray energy, or waiting-time features when those signals are relevant? These checks should be included as visual examples in the final defense.

The ninth class concerns dashboard usefulness. A judge should be able to understand the current solar state, risk, confidence, anomaly signal, and explanation within seconds. Evaluation of the dashboard should include scenario walkthroughs: quiet Sun, rising pre-flare behavior, high-risk event, uncertain conflicting signals, and anomalous non-flare behavior. The demo script should show how the system supports decisions, not just how charts animate.

The final evaluation principle is traceability. Every number in the submission should be reproducible from a known dataset split and model run. Every qualitative example should identify the date, event, data sources, and model version. This discipline will separate Project Solaris from submissions that look impressive but cannot defend their evidence.

## Part X: Productization

Project Solaris should be designed as an operational decision-support platform, not only a research model. Productization begins with the user workflow. A space-weather analyst opens the dashboard, observes current or replayed soft and hard X-ray behavior, sees a risk gauge, reviews confidence, checks anomaly index, examines explanation panels, and decides whether the warning deserves attention. The system should support scanning, comparison, and repeated use. It should not behave like a one-time demo page.

The product should communicate four states clearly: normal, watch, warning, and critical. Normal indicates low risk and low anomaly. Watch indicates rising signals or uncertainty that deserves attention. Warning indicates elevated flare probability with meaningful confidence or supporting anomaly evidence. Critical indicates high risk, possible severe class, low uncertainty, or strong mission relevance. These states should be defined mathematically in terms of probability, uncertainty, anomaly index, and severity estimate. Visual styling should support quick interpretation without turning the dashboard into decoration.

The first product mode should be replay mode. Because the hackathon uses historical or prepared data, replay mode allows the team to demonstrate how the system would behave as a flare develops. The user can select a historical event, play the timeline, and watch risk, uncertainty, anomaly index, and explanations evolve. This is more compelling than a static prediction table. It also makes lead time visible.

The second product mode should be analysis mode. It allows deeper inspection of a chosen interval: raw and normalized signals, engineered features, attention heatmap, attribution chart, Neupert consistency, anomaly reconstruction error, and event label. This mode is useful for judges who want technical depth. The interface should keep the main mission view uncluttered while making detailed evidence available.

The future operational mode would connect to live or near-real-time data feeds. In that mode, the system would need robust ingestion, data quality checks, alert thresholds, audit logs, uptime monitoring, fallback behavior, and user-role controls. These are beyond the hackathon implementation, but the architecture should not block them. The dashboard should be written so that historical replay and live inference share the same output schema.

Productization also includes reporting. The system should generate event summaries that can be used in mission briefings: time interval, risk trajectory, maximum probability, confidence band, anomaly peak, top explanatory features, predicted severity, and recommended attention level. These summaries can become part of a future operational log. They also support the hackathon defense because they show how outputs become decisions.

The SEP extension belongs in productization because particle risk is a decision concern. The first version can include a radiation-risk panel labeled as experimental or future-facing. It should connect flare severity and uncertainty to mission contexts such as satellite operations, Gaganyaan, Bharatiya Antariksha Station, and astronaut safety. The panel should be careful with language. It can say that a high-energy flare may increase attention to particle-risk monitoring. It should not claim validated SEP arrival prediction unless particle data and evaluation are added.

The product should be designed for Indian space-weather capability. That means using Aditya-L1 language, payload-aware explanations, and ISRO mission relevance. It also means avoiding overreliance on generic Western operational framing. NOAA and NASA data are valuable proxies and references, but the project story should return to Aditya-L1 and Indian operational needs. The product name Solaris should become associated with this bridge: solar physics, Indian mission data, AI forecasting, and operational readiness.

The path to a future platform includes several stages. Stage one is the hackathon demonstrator using proxy data. Stage two is a research-grade prototype with stronger validation and Aditya-L1 integration when available. Stage three is an analyst dashboard with operational workflows. Stage four is an API and alerting service. Stage five is a broader space-weather decision-support platform that includes flare, SEP, geomagnetic, satellite-risk, and human-spaceflight modules. The Constitution does not require all stages now, but it keeps the direction coherent.

## Part XI: Execution

Execution should follow the documentation hierarchy. DOC-001 is this Constitution. DOC-002 should be the decision log. DOC-101 should be the idea submission. DOC-102 should be the project definition report. DOC-103 should become the presentation. Research documents should include space weather review, Aditya-L1 payload analysis, and physics foundation. System documents should include system design, data architecture, ML architecture, and dashboard architecture. Execution documents should include hackathon roadmap, task board, and risk register. Defense documents should include judge question bank, technical defense handbook, and demo script.

The first execution rule is sequence discipline. Do not build the dashboard before the system story is stable. Do not tune the model before the data pipeline and labels are credible. Do not write the pitch before the thesis is clear. The Constitution exists to prevent chaotic parallel work from creating inconsistent artifacts. Once this document is accepted, the team should derive the next documents in order of dependency.

The recommended milestone sequence begins with documentation and data. Milestone one is DOC-001 completion. Milestone two is DOC-002 decision log creation and initial decisions recorded. Milestone three is data source acquisition and feasibility check. Milestone four is feature engineering and label pipeline. Milestone five is baseline models. Milestone six is Dual-Branch Cross-Attention GRU. Milestone seven is physics loss. Milestone eight is uncertainty. Milestone nine is anomaly detection. Milestone ten is dashboard replay mode. Milestone eleven is evaluation and ablations. Milestone twelve is submission writing, presentation, defense handbook, and demo script.

Roles should be divided by responsibility, not by isolated tasks. One team member should own data and labels. One should own model architecture and experiments. One should own dashboard and visual communication. One should own documentation, narrative, and defense. If the team is small, one person can hold multiple roles, but responsibilities should still be explicit. Every role should feed into the Constitution and decision log.

The decision log is mandatory because the project will face tradeoffs. Examples include forecast horizon selection, flare threshold selection, data cadence, proxy dataset choice, missing-data treatment, model dimensionality, physics-loss weight, anomaly threshold, dashboard alert thresholds, and whether to include optional 3D spectrograms. Each decision should record the context, options considered, choice, rationale, consequences, and date. This helps the team defend decisions under questioning.

The task board should distinguish must-have, should-have, and could-have items. Must-have items are the data pipeline, mandatory features, primary forecast model, uncertainty output, anomaly index, basic explanation, evaluation, and mission dashboard. Should-have items include ablations, calibration plots, attention heatmap polish, multiple forecast horizons, and richer event replay. Could-have items include 3D time-energy spectrograms, advanced SEP panel, model comparison leaderboard, and animated mission visuals. Optional items must not consume time before the core system works.

The risk register should include data availability risk, alignment risk between proxy datasets, class imbalance risk, model overfitting risk, physics-loss misuse risk, explanation complexity risk, dashboard scope creep, performance under weak events, and narrative overclaiming. Each risk should have mitigation. For example, if RHESSI hard X-ray processing is too slow, use a smaller curated subset or Fermi GBM proxy. If SHAP integration is unstable, use permutation importance and temporal attribution. If the physics loss hurts performance, report ablation honestly and keep it as a diagnostic or lightly weighted term.

Execution should preserve a working demo at all times after the first model exists. The team should not wait until the final day to assemble the dashboard. A simple replay demo with baseline outputs is better than a sophisticated model that cannot be shown. Once the replay pipeline exists, it can be improved incrementally. This also protects against late failures.

The final hackathon package should include the working dashboard, concise presentation, project definition report, evaluation results, architecture diagram, demo script, and defense handbook. The Constitution itself may be too long for judges to read in full, but it will strengthen every derived artifact. Its presence also shows that the team has treated the problem as a serious system, not a weekend classifier.

## Part XII: Defense

The defense posture must be clear, confident, and scientifically honest. The project should open with the mission impact: solar flares and related space-weather events affect satellites, communications, navigation, and future human spaceflight. India now has Aditya-L1 as a solar mission, creating an opportunity to develop indigenous, payload-aware space-weather intelligence. Project Solaris turns dual-band X-ray observations into early warning, uncertainty, explanation, anomaly detection, and mission risk context.

The core defense statement is: most systems ask whether a flare will occur; Project Solaris asks whether a flare will occur, how confident the system is, why the system believes it, whether the Sun is behaving unusually, and what the potential mission implication may be. This statement should be repeated in the presentation, demo, and judge answers. It is the clearest positioning against generic models.

When asked why the project uses a Dual-Branch Cross-Attention GRU instead of a Transformer, the answer should be pragmatic and mission-centered. The chosen architecture balances performance, feasibility, explainability, and hackathon constraints. Separate GRU branches preserve soft and hard X-ray modality identity. Cross-attention models interactions between thermal and non-thermal signals. The architecture is easier to train and defend on constrained data than a large Transformer. The goal is not to win an architecture fashion contest; the goal is to build a credible early warning system.

When asked why physics-informed learning matters, the answer should reference the Neupert effect. The relationship between hard X-ray emission and the derivative of soft X-ray emission gives the model a meaningful physical prior. The system does not force the relationship as an absolute rule. It uses it as a soft training constraint and diagnostic signal. This improves scientific credibility and helps the explanation layer connect model behavior to flare physics.

When asked why uncertainty is mandatory, the answer should be operational. Space-weather decisions cannot rely on a single probability without confidence context. A 70 percent risk with low uncertainty is not the same as a 70 percent risk with high uncertainty. Monte Carlo Dropout provides a feasible way to estimate prediction variance. The dashboard communicates this so operators can calibrate attention and avoid false precision.

When asked why anomaly detection is separate, the answer should be that unusual solar behavior is not identical to supervised flare probability. A GRU autoencoder trained on quiet or normal intervals can detect departures from learned behavior. Its anomaly index becomes an independent warning channel. This helps catch unusual pre-flare dynamics and provides another signal for operators.

When asked about data limitations, the answer should be transparent. The hackathon prototype uses public proxy data such as GOES XRS, RHESSI, Fermi GBM, and NOAA flare catalogs because direct operational use of Aditya-L1 payload data may not be available in the required format or time. The architecture is designed around the future SoLEXS and HEL1OS target identity. Proxy use is a practical demonstration strategy, not a claim that the datasets are identical.

When asked about SEP risk, the answer should avoid overclaiming. The project includes SEP risk as a future extension because radiation protection matters for Gaganyaan, Bharatiya Antariksha Station, satellites, and human spaceflight. The first implementation may provide a lightweight risk context based on flare severity and hard X-ray behavior, but full SEP forecasting requires additional particle data and validation. This honesty strengthens the defense.

When asked how the system helps ISRO, the answer should connect directly to mission capability. It supports an Indian solar mission context, transforms payload-relevant measurements into warning products, provides explanations that scientists can inspect, quantifies uncertainty, and creates a pathway toward operational decision support. It also demonstrates how AI can be integrated with physics rather than replacing scientific reasoning.

The defense should include limitations before judges force them out. The team should say that the first version is a hackathon demonstrator using proxy data, simplified horizons, and constrained evaluation. It is not an operational service yet. Then the team should explain the roadmap to operational maturity: Aditya-L1 integration, longer validation, improved calibration, SEP data, analyst workflow testing, and operational reliability. Owning limitations makes the ambition more credible.

The final defense tone should be serious but not inflated. Project Solaris is ambitious because the problem deserves ambition. It is credible because the architecture, features, losses, uncertainty, explanations, and documentation all follow from the same mission thesis.

## Appendices

### Appendix A: Documentation Hierarchy

The Project Solaris documentation system is organized as follows:

DOC-001 Project Solaris Constitution. This is the master source of truth.  
DOC-002 Decision Log. This records major scientific, technical, and product decisions.  
DOC-101 Idea Submission. This is derived from the Constitution for hackathon submission.  
DOC-102 Project Definition Report. This formalizes scope, objectives, and deliverables.  
DOC-103 Presentation. This translates the project into a judge-facing slide deck.  
DOC-201 Space Weather Research Review. This summarizes domain and operational background.  
DOC-202 Aditya-L1 Payload Analysis. This studies SoLEXS, HEL1OS, and mission context.  
DOC-203 Physics Foundation. This explains flare physics, X-ray behavior, and Neupert effect.  
DOC-301 System Design Document. This defines end-to-end architecture.  
DOC-302 Data Architecture. This defines datasets, pipelines, labels, and feature engineering.  
DOC-303 ML Architecture. This defines the model, training, losses, uncertainty, and anomaly detection.  
DOC-304 Dashboard Architecture. This defines interface, screens, data contracts, and demo modes.  
DOC-401 Hackathon Roadmap. This sequences execution milestones.  
DOC-402 Task Board. This tracks actionable work.  
DOC-403 Risk Register. This tracks risks and mitigations.  
DOC-501 Judge Question Bank. This prepares likely questions and answers.  
DOC-502 Technical Defense Handbook. This prepares detailed scientific and engineering defense.  
DOC-503 Demo Script. This defines the final presentation and dashboard walkthrough.

No document should contradict DOC-001 without a recorded decision in DOC-002.

### Appendix B: Canonical Architecture Summary

The canonical architecture is:

Data Layer -> Feature Engineering -> Soft X-Ray Encoder -> Hard X-Ray Encoder -> Cross-Attention Fusion -> Physics Constraint Layer -> Forecasting Head -> Uncertainty Layer -> Explainability Layer -> Mission Dashboard.

In parallel, a GRU Autoencoder produces the Anomaly Index. A lightweight SEP-risk extension provides future mission relevance. The preferred model family is Dual-Branch Cross-Attention GRU. The preferred uncertainty method is Monte Carlo Dropout. The preferred physics-informed component is Neupert-aware loss and diagnostic scoring.

### Appendix C: Mandatory Features

The mandatory feature set includes soft X-ray flux, hard X-ray flux, hardness ratio, soft X-ray derivative, integrated hard X-ray energy, waiting-time statistics, rolling mean, rolling variance, rolling slope, and rolling volatility. These features should be computed without future leakage and should preserve enough physical meaning to be explained in the dashboard.

### Appendix D: Required Dashboard Components

The dashboard must include live or replayable soft X-ray plot, hard X-ray plot, flare risk gauge, time-to-flare estimate where feasible, confidence interval, anomaly index, attribution or SHAP explanation, and attention heatmap. Optional additions include a 3D time-energy spectrogram, but only after the core workflow is reliable.

### Appendix E: Initial Risk Register

Data availability risk: proxy datasets may be difficult to align or may have gaps. Mitigation: start with a minimal reliable subset and document all assumptions.

Class imbalance risk: major flares are rare. Mitigation: use event-aware splits, PR-AUC, recall, false alarm metrics, and balanced sampling strategies.

Overfitting risk: a deep model may learn dataset artifacts. Mitigation: use baselines, temporal validation, regularization, and ablation studies.

Physics-loss risk: Neupert regularization may be too rigid. Mitigation: use it as a soft weighted loss, validate lambda, and report ablations.

Explanation risk: SHAP or attention may be misinterpreted. Mitigation: present explanations as diagnostic aids and pair them with physical feature plots.

Dashboard scope risk: optional visuals may distract from core function. Mitigation: build replay mode and required panels first.

Narrative overclaim risk: the project may sound operational before it is validated. Mitigation: clearly separate hackathon prototype, research prototype, and future operational system.

### Appendix F: Source References

The Constitution is based first on the Project Solaris handoff document provided to the team. External factual grounding should use official or primary sources wherever possible, including:

- ISRO Aditya-L1 mission and payload information: https://www.isro.gov.in/Aditya_L1.html
- NOAA Space Weather Prediction Center solar flare and GOES X-ray information: https://www.swpc.noaa.gov/
- NASA RHESSI mission information: https://science.nasa.gov/mission/rhessi/
- NASA Fermi Gamma-ray Burst Monitor information: https://gammaray.nsstc.nasa.gov/gbm/
- NASA and heliophysics educational material on solar flares and space weather: https://science.nasa.gov/sun/

Future derived documents should expand these references with exact dataset pages, instrument papers, data access notes, preprocessing citations, and model-method references.

