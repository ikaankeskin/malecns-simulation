# MaleCNS Simulation

A minimal, inspectable 2D foraging loop. It takes a directed weighted neuron graph, applies bounded continuous activity updates, maps sensory inputs and motor outputs, and records every tick. **This is an exploratory controller, not a biological reconstruction.** The included `demo.json` is synthetic and is explicitly not MaleCNS data.

## Project plan

See [PLAN.md](PLAN.md) for milestones, scientific controls, current status, and the commit workflow. Each completed implementation step is committed separately. Contributor instructions are in [AGENTS.md](AGENTS.md).

## Run now (Python 3.9+, standard library)

```bash
python3 sim.py run demo.json --ticks 120 --out trace.json
```

The output records position, heading, food location, motor activity, and collection events. A fixed seed makes runs repeatable.

## Insert a real MaleCNS circuit

Janelia publishes MaleCNS v1.0 annotations (~13 MB), neuron neurotransmitter predictions (~42 MB), and full connectome weights (~1.1 GB) at https://male-cns.janelia.org/download/ under CC BY. Export a *selected* circuit to CSV with these columns:

- `nodes.csv`: `id,role,side` with `role` set to `sensory`, `interneuron`, or `motor`, and `side` set to `left`, `right`, or `center`. IDs must be actual MaleCNS segment IDs. The assigned roles and mapping to the virtual world are hypotheses to document.
- `edges.csv`: `body_pre,body_post,weight` with real directed synapse counts for those IDs.

```bash
python3 sim.py import-csv nodes.csv edges.csv circuit.json --limit 1000
python3 sim.py run circuit.json --ticks 120 --out trace.json
```

**Current boundary:** The importer does not fetch or choose biological circuits. A real-data run requires the official dataset export and a justified sensory/motor mapping. It does not infer inhibitory signs from neurotransmitter annotations, implement spikes, or learn via plasticity. The toy activity equation is `next = clip(0.75*activity + 0.25*(weighted input + stimulus), 0, 1)`; edge weights are scaled by 100 and clipped. These are engineering assumptions, not measured physiological parameters.

Next experiment: choose a small annotated visual-to-descending-neuron pathway in neuPrint, export the selected edges and IDs, run an ablation against the synthetic controller, and evaluate whether the real topology yields responsive movement. Keep data attribution and dataset version with every exported circuit.


## Data attribution

MaleCNS is produced by FlyEM (HHMI Janelia), the University of Cambridge Department of Zoology, the MRC Laboratory of Molecular Biology, and Google Research. Official data is distributed under CC BY; retain the specific release license and citation with derived extracts. No real MaleCNS data is included in the current baseline. Source: https://male-cns.janelia.org/download/.
