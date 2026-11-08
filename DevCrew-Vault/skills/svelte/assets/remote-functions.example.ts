// Example: Remote functions for type-safe client-server communication
// File: data.remote.ts

import { query, form, command, prerender } from '$app/server';
import * as v from 'valibot';
import { error, redirect } from '@sveltejs/kit';
import * as db from '$lib/server/database';
import * as auth from '$lib/server/auth';

// Query - Read data from server
export const getPosts = query(async () => {
	const posts = await db.sql`
		SELECT title, slug, published_at
		FROM posts
		ORDER BY published_at DESC
	`;
	return posts;
});

// Query with validation
export const getPost = query(v.string(), async (slug) => {
	const [post] = await db.sql`
		SELECT * FROM posts
		WHERE slug = ${slug}
	`;
	
	if (!post) error(404, 'Post not found');
	return post;
});

// Form - Handle form submissions
export const createPost = form(async (data) => {
	// Check authentication
	const user = await auth.getUser();
	if (!user) error(401, 'Unauthorized');
	
	// Validate data
	const title = data.get('title');
	const content = data.get('content');
	
	if (typeof title !== 'string' || typeof content !== 'string') {
		error(400, 'Invalid data');
	}
	
	const slug = title.toLowerCase().replace(/ /g, '-');
	
	// Insert into database
	await db.sql`
		INSERT INTO posts (slug, title, content, author_id)
		VALUES (${slug}, ${title}, ${content}, ${user.id})
	`;
	
	// Refresh queries
	await getPosts().refresh();
	
	// Redirect to new post
	redirect(303, `/blog/${slug}`);
});

// Command - Programmatic writes
export const addLike = command(v.string(), async (postId) => {
	await db.sql`
		UPDATE posts
		SET likes = likes + 1
		WHERE id = ${postId}
	`;
	
	// Refresh the post query
	getPost(postId).refresh();
});

// Prerender - Static data at build time
export const getCategories = prerender(async () => {
	const categories = await db.sql`
		SELECT id, name, slug
		FROM categories
		ORDER BY name
	`;
	return categories;
});

// Prerender with arguments
export const getCategoryPosts = prerender(
	v.string(),
	async (categorySlug) => {
		const posts = await db.sql`
			SELECT p.*
			FROM posts p
			JOIN categories c ON p.category_id = c.id
			WHERE c.slug = ${categorySlug}
		`;
		return posts;
	},
	{
		inputs: () => ['tech', 'design', 'business'],
		dynamic: true
	}
);
