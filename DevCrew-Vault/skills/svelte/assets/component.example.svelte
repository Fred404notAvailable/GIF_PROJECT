<script lang="ts">
	// Example: Svelte 5 component with runes

	// Props with TypeScript interface
	interface Props {
		title: string;
		count?: number;
		onIncrement?: (newCount: number) => void;
	}

	let { title, count = 0, onIncrement = () => {} }: Props = $props();

	// Local state
	let localCount = $state(count);

	// Derived state
	let doubled = $derived(localCount * 2);
	let isEven = $derived(localCount % 2 === 0);

	// Effect (use sparingly)
	$effect(() => {
		console.log(`Count changed to ${localCount}`);
	});

	// Event handler
	function handleClick() {
		localCount++;
		onIncrement(localCount);
	}
</script>

<div class="card">
	<h2>{title}</h2>
	
	<p>Count: {localCount}</p>
	<p>Doubled: {doubled}</p>
	<p>Is even: {isEven ? 'Yes' : 'No'}</p>
	
	<button onclick={handleClick}>
		Increment
	</button>
</div>

<style>
	.card {
		padding: 1rem;
		border: 1px solid #ccc;
		border-radius: 0.5rem;
	}
</style>
