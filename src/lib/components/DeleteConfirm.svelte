<script lang="ts">
  import AppDialog from "./AppDialog.svelte";

  let {
    title = "Confirm Delete",
    message = "Are you sure you want to delete this item?",
    onConfirm,
    onCancel,
  }: {
    title?: string;
    message?: string;
    onConfirm: () => void;
    onCancel: () => void;
  } = $props();
</script>

<AppDialog
  {title}
  {message}
  confirmLabel="Delete"
  cancelLabel="Cancel"
  showCancel={true}
  tone="error"
  {onConfirm}
  {onCancel}
/>
