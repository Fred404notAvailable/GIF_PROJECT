// Example: State management with classes
// File: counter.svelte.ts

class Counter {
	count = $state(0);
	incrementor = $state(1);

	increment = () => {
		this.count += this.incrementor;
	};

	decrement = () => {
		this.count -= this.incrementor;
	};

	resetCount = () => {
		this.count = 0;
	};

	resetIncrementor = () => {
		this.incrementor = 1;
	};
}

export const counter = new Counter();
