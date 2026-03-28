import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import CommunityPage from '../page'
import { CommunityPost } from '@/services/community'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
  usePathname: () => '/community',
}))

// Mock data
const mockPosts: CommunityPost[] = [
    {
        id: '1',
        title: 'First Post',
        content: 'This is the content of the first post',
        user_id: 'user1',
        post_type: 'discussion',
        district: 'District 1',
        is_admin_override: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        likes_count: 5,
        replies_count: 2,
        user_has_liked: false,
        author_name: 'John Doe',
        image_url: 'http://example.com/image.jpg'
    },
    {
        id: '2',
        title: 'Second Post',
        content: 'This is the content of the second post',
        user_id: 'user2',
        post_type: 'question',
        district: 'District 2',
        is_admin_override: false,
        created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
        updated_at: new Date(Date.now() - 86400000).toISOString(),
        likes_count: 10,
        replies_count: 0,
        user_has_liked: true,
        author_name: 'Jane Smith'
    }
]

// API Handlers
const handlers = [
    // Get posts
    http.get('*/community/posts/', () => {
        return HttpResponse.json({
            items: mockPosts,
            total: mockPosts.length,
            skip: 0,
            limit: 100
        })
    }),

    // Search posts
    http.get('*/community/posts/search', ({ request }) => {
        const url = new URL(request.url)
        const q = url.searchParams.get('q')
        if (q === 'First') {
            return HttpResponse.json(mockPosts.filter(p => p.title.includes('First')))
        }
        return HttpResponse.json([])
    }),

    // Get posts by type
    http.get('*/community/posts/type/:type', ({ params }) => {
        const { type } = params
        return HttpResponse.json(mockPosts.filter(p => p.post_type === type))
    }),

    // Create post
    http.post('*/community/posts/', async ({ request }) => {
        const data = await request.json() as any
        return HttpResponse.json({
            id: '3',
            ...data,
            user_id: 'current-user',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            likes_count: 0,
            replies_count: 0,
            user_has_liked: false,
            author_name: 'Current User'
        })
    }),

    // Upvote
    http.post('*/community/posts/:id/upvote', () => {
        return new HttpResponse(null, { status: 200 })
    }),

    // Remove upvote
    http.delete('*/community/posts/:id/upvote', () => {
        return new HttpResponse(null, { status: 200 })
    }),

    // Get replies
    http.get('*/community/posts/:id/replies', () => {
        return HttpResponse.json([
            {
                id: 'r1',
                post_id: '1',
                user_id: 'user2',
                content: 'This is a reply',
                created_at: new Date().toISOString(),
                author_name: 'Jane Smith'
            }
        ])
    }),

    // Add reply
    http.post('*/community/posts/:id/reply', async ({ request }) => {
        const data = await request.json() as any
        return HttpResponse.json({
            id: 'r2',
            post_id: '1',
            user_id: 'current-user',
            content: data.content,
            created_at: new Date().toISOString(),
            author_name: 'Current User'
        })
    }),

    // Update Post
    http.put('*/community/posts/:id', async ({ request }) => {
        const data = await request.json() as any
        return HttpResponse.json({
            id: '1',
            title: data.title,
            content: data.content,
            user_id: 'user1',
            post_type: 'discussion',
            district: 'District 1',
            is_admin_override: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            likes_count: 5,
            replies_count: 2,
            user_has_liked: false,
            author_name: 'John Doe',
        })
    }),

    // Delete Post
    http.delete('*/community/posts/:id', () => {
        return new HttpResponse(null, { status: 200 })
    })

]

const server = setupServer(...handlers)

// Setup
beforeAll(() => server.listen())
afterEach(() => {
    server.resetHandlers()
    vi.clearAllMocks()
    localStorage.clear()
})
afterAll(() => server.close())

// Helper to mock logged in user
const mockLogin = () => {
    localStorage.setItem('token', 'fake-token')
    localStorage.setItem('user', JSON.stringify({ id: 'current-user', name: 'Current User' }))
}

describe('CommunityPage', () => {
    it('1. Rendering: Page title displays', async () => {
        render(<CommunityPage />)
        expect(screen.getByText('Farmer Community Forum')).toBeInTheDocument()
        expect(screen.getByText('Share knowledge, ask questions, and connect with fellow farmers')).toBeInTheDocument()
    })

    it('1. Rendering: Create Post button visible', async () => {
        render(<CommunityPage />)
        expect(screen.getByRole('button', { name: /create post/i })).toBeVisible()
    })

    it('1. Rendering: Category tabs render', async () => {
        render(<CommunityPage />)
        expect(screen.getByRole('button', { name: 'All' })).toBeVisible()
        expect(screen.getByRole('button', { name: 'General' })).toBeVisible()
        expect(screen.getByRole('button', { name: 'Question' })).toBeVisible()
        expect(screen.getByRole('button', { name: 'Tip' })).toBeVisible()
        expect(screen.getByRole('button', { name: 'Alert' })).toBeVisible()
    })

    it('3. Post Display: Posts render in list', async () => {
        render(<CommunityPage />)

        await waitFor(() => {
            expect(screen.getByText('First Post')).toBeInTheDocument()
            expect(screen.getByText('Second Post')).toBeInTheDocument()
        })

        expect(screen.getByText('This is the content of the first post')).toBeInTheDocument()
        expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    it('3. Post Display: Category badges show correct color', async () => {
        render(<CommunityPage />)
        await waitFor(() => screen.getByText('First Post'))

        // Find badges within the post cards (not the filter buttons)
        // Badges have data-slot="badge" attribute from shadcn Badge component
        const badges = screen.getAllByText('General')
        // The first one is the filter button, find the badge which has bg-blue-100
        const generalBadge = badges.find(el => el.classList.contains('bg-blue-100'))
        expect(generalBadge).toBeTruthy()

        const questionBadges = screen.getAllByText('Question')
        const questionBadge = questionBadges.find(el => el.classList.contains('bg-green-100'))
        expect(questionBadge).toBeTruthy()
    })

    it('3. Post Display: Upvote and Reply count displays', async () => {
        render(<CommunityPage />)
        await waitFor(() => {
            expect(screen.getByText('5')).toBeInTheDocument() // First post likes
            expect(screen.getByText('2')).toBeInTheDocument() // First post replies
            expect(screen.getByText('10')).toBeInTheDocument() // Second post likes
        })
    })

    it('2. Post Creation: Form opens on button click', async () => {
        render(<CommunityPage />)
        fireEvent.click(screen.getByRole('button', { name: /create post/i }))
        expect(screen.getByText('Create New Post')).toBeInTheDocument()
    })

    it('2. Post Creation: All fields render', async () => {
        render(<CommunityPage />)
        fireEvent.click(screen.getByRole('button', { name: /create post/i }))

        expect(screen.getByPlaceholderText('Enter post title')).toBeVisible()
        expect(screen.getByPlaceholderText('Write your post content...')).toBeVisible()
        expect(screen.getByText('Category')).toBeVisible()
        expect(screen.getByText('Image (optional)')).toBeVisible()
    })

    it('2. Post Creation: Submit disabled when invalid', async () => {
        render(<CommunityPage />)
        fireEvent.click(screen.getByRole('button', { name: /create post/i }))

        const submitBtn = screen.getByRole('button', { name: /^Post$/ })
        expect(submitBtn).toBeDisabled()

        fireEvent.change(screen.getByPlaceholderText('Enter post title'), { target: { value: 'Hi' } }) // Too short
        expect(submitBtn).toBeDisabled()
    })

    it('2. Post Creation: Success creates post and closes form', async () => {
        mockLogin()
        render(<CommunityPage />)

        // Open form
        fireEvent.click(screen.getByRole('button', { name: /create post/i }))

        // Fill form
        fireEvent.change(screen.getByPlaceholderText('Enter post title'), { target: { value: 'New Test Post' } })
        fireEvent.change(screen.getByPlaceholderText('Write your post content...'), { target: { value: 'This is a test post content that is long enough.' } })

        // Submit
        const submitBtn = screen.getByRole('button', { name: /^Post$/ })
        await waitFor(() => expect(submitBtn).not.toBeDisabled())
        fireEvent.click(submitBtn)

        // Check result
        await waitFor(() => {
            expect(screen.queryByText('Create New Post')).not.toBeInTheDocument()
        })
        // Ideally we should see the new post, but our mock returns ID 3 which mockPosts doesn't have initially.
        // But the component adds it to state.
        expect(screen.getByText('New Test Post')).toBeInTheDocument()
    })

    it('4. Filtering: Category filter works', async () => {
        render(<CommunityPage />)
        await waitFor(() => screen.getByText('First Post'))

        // Click Question filter
        fireEvent.click(screen.getByRole('button', { name: 'Question' }))

        await waitFor(() => {
            expect(screen.queryByText('First Post')).not.toBeInTheDocument()
            expect(screen.getByText('Second Post')).toBeInTheDocument()
        })
    })

    it('4. Filtering: Search filters posts', async () => {
        render(<CommunityPage />)
        await waitFor(() => screen.getByText('Second Post'))

        const searchInput = screen.getByPlaceholderText('Search posts...')
        fireEvent.change(searchInput, { target: { value: 'First' } })

        await waitFor(() => {
            expect(screen.getByText('First Post')).toBeInTheDocument()
            expect(screen.queryByText('Second Post')).not.toBeInTheDocument()
        })
    })

    it('5. Interactions: Upvote toggles correctly', async () => {
        mockLogin()
        render(<CommunityPage />)
        await waitFor(() => screen.getByText('5'))

        // Find the button with text '5'
        const upvoteBtn = screen.getByText('5').closest('button')!
        fireEvent.click(upvoteBtn)

        await waitFor(() => {
            expect(screen.getByText('6')).toBeInTheDocument()
        })
    })

    it('5. Interactions: Reply opens detail view', async () => {
        render(<CommunityPage />)
        await waitFor(() => screen.getByText('First Post'))

        // Click on the post card (use h3 selector to get the title in the list)
        const postTitle = screen.getByRole('heading', { name: 'First Post', level: 3 })
        fireEvent.click(postTitle)

        await waitFor(() => {
            const dialog = screen.getByRole('dialog')
            expect(dialog).toBeVisible()
            // The dialog title is an h2 with data-slot="dialog-title"
            const dialogTitle = within(dialog).getByRole('heading', { level: 2 })
            expect(dialogTitle).toHaveTextContent('First Post')
        })
    })

    it('5. Interactions: Delete shows confirmation', async () => {
        // Mock author is current user for First Post
        mockLogin()
        // We need to override the mockPosts or component logic for "isAuthor"
        // The component checks local storage user ID against post.user_id.
        // First Post user_id is 'user1'. Let's change our mock login to use 'user1'.
        localStorage.setItem('user', JSON.stringify({ id: 'user1', name: 'John Doe' }))

        render(<CommunityPage />)
        await waitFor(() => screen.getByText('First Post'))

        // Click delete button (trash icon)
        // Need to be careful about which delete button if there are multiple posts.
        // Rendered posts: First Post (author=user1), Second Post (author=user2)
        // We are logged in as user1. So First Post should have delete button.

        const deleteBtns = screen.getAllByRole('button').filter(btn => btn.querySelector('.lucide-trash-2'))
        expect(deleteBtns.length).toBeGreaterThan(0)

        fireEvent.click(deleteBtns[0])

        expect(screen.getByText('Delete Post')).toBeVisible()
        expect(screen.getByText('Are you sure you want to delete this post? This action cannot be undone.')).toBeVisible()
    })

})
