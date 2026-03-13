# Controller Workflows Reference

This directory contains controller workflow definitions — step-by-step procedures for operating a multi_agent_ide controller session.

## How to manage workflows

- **Adding**: Create a new `<descriptive-name>.md` file in this directory and add a row to the table below. Use the standard workflow as a template for structure.
- **Editing**: Update the workflow file directly. If an edit makes the workflow strictly better, apply it in place. If it's experimental, create a variant instead.
- **Removing**: Delete the file and remove its row from this table. Only remove a workflow if it's been superseded or proven unworkable.
- **Variants**: When you try an experimental approach (e.g., tighter poll loop, different resolution strategy), create it as a separate file so it can be compared against the standard.

## Workflows

| Workflow | File | Description |
|----------|------|-------------|
| Standard | `standard_workflow.md` | **The canonical controller loop.** Push/sync → deploy → start goal → poll workflow-graph → handle blocked states → continue polling → redeploy. Start here. |
<!-- Add new workflows as they are created -->
