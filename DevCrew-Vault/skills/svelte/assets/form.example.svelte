<script lang="ts">
	// Example: Form with Shadcn components and validation
	import * as Form from '$lib/components/ui/form';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { formFieldProxy, superForm } from 'sveltekit-superforms';
	import { zodClient } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	// Define validation schema
	const formSchema = z.object({
		title: z.string().min(3, 'Title must be at least 3 characters'),
		content: z.string().min(10, 'Content must be at least 10 characters'),
		email: z.string().email('Invalid email address'),
		category: z.enum(['tech', 'design', 'business'])
	});

	// Get form data from page data
	let { data } = $props();

	// Initialize superForm
	const form = superForm(data.form, {
		validators: zodClient(formSchema),
		onUpdated: ({ form }) => {
			if (form.valid) {
				console.log('Form submitted successfully!');
			}
		}
	});

	const { form: formData, enhance } = form;

	// Create field proxies for reactive access
	const title = formFieldProxy(form, 'title');
	const content = formFieldProxy(form, 'content');
	const email = formFieldProxy(form, 'email');
	const category = formFieldProxy(form, 'category');
</script>

<div class="max-w-2xl mx-auto p-6">
	<h1 class="text-3xl font-bold mb-6">Create New Post</h1>

	<form method="POST" use:enhance class="space-y-6">
		<!-- Title Field -->
		<Form.Field {form} name="title">
			<Form.Control let:attrs>
				<Form.Label>Title</Form.Label>
				<Input
					{...attrs}
					bind:value={$title}
					placeholder="Enter post title"
				/>
			</Form.Control>
			<Form.Description>
				Choose a descriptive title for your post
			</Form.Description>
			<Form.FieldErrors />
		</Form.Field>

		<!-- Content Field -->
		<Form.Field {form} name="content">
			<Form.Control let:attrs>
				<Form.Label>Content</Form.Label>
				<Textarea
					{...attrs}
					bind:value={$content}
					placeholder="Write your post content"
					rows={10}
				/>
			</Form.Control>
			<Form.FieldErrors />
		</Form.Field>

		<!-- Email Field -->
		<Form.Field {form} name="email">
			<Form.Control let:attrs>
				<Form.Label>Email</Form.Label>
				<Input
					{...attrs}
					type="email"
					bind:value={$email}
					placeholder="your@email.com"
				/>
			</Form.Control>
			<Form.Description>
				We'll send you a confirmation email
			</Form.Description>
			<Form.FieldErrors />
		</Form.Field>

		<!-- Category Field -->
		<Form.Field {form} name="category">
			<Form.Control let:attrs>
				<Form.Label>Category</Form.Label>
				<select {...attrs} bind:value={$category} class="w-full p-2 border rounded">
					<option value="">Select a category</option>
					<option value="tech">Technology</option>
					<option value="design">Design</option>
					<option value="business">Business</option>
				</select>
			</Form.Control>
			<Form.FieldErrors />
		</Form.Field>

		<!-- Submit Button -->
		<Form.Button class="w-full">
			Create Post
		</Form.Button>
	</form>
</div>
