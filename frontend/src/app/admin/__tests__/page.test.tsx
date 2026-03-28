import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ---------- Hoisted variables for use in vi.mock factories ----------
const { mockPush, mockRouter, mockStats, mockUsers, mockPosts, getQueryOverrides } = vi.hoisted(() => {
  let _queryOverrides: Record<string, any> = {}
  const push = vi.fn()
  return {
    mockPush: push,
    // CRITICAL: stable router reference to avoid infinite re-render loop
    // Admin page has useEffect(..., [router]) — new object each call = infinite loop
    mockRouter: { push, back: vi.fn(), replace: vi.fn(), refresh: vi.fn(), prefetch: vi.fn(), forward: vi.fn() },
    mockStats: { total_users: 120, total_posts: 45, banned_users: 3 },
    mockUsers: [
      { id: 'u1', name: 'Ravi Kumar', phone: '9876543210', phone_number: '9876543210', location: 'Thrissur', created_at: '2025-11-15T10:00:00Z', is_banned: false },
      { id: 'u2', name: 'Priya Nair', phone: '9876543211', phone_number: '9876543211', location: 'Ernakulam', created_at: '2025-12-01T10:00:00Z', is_banned: true },
    ],
    mockPosts: [
      { id: 'p1', title: 'Rice prices rising', author_name: 'Ravi Kumar', category: 'discussion', created_at: '2026-01-10T10:00:00Z', likes_count: 10, comments_count: 3 },
      { id: 'p2', title: 'Tomato harvest tips', author_name: 'Priya Nair', category: 'tip', created_at: '2026-01-12T10:00:00Z', likes_count: 5, comments_count: 1 },
    ],
    getQueryOverrides: () => _queryOverrides,
  }
})

function setQueryOverride(key: string, value: any) {
  const overrides = getQueryOverrides()
  overrides[key] = value
}
function clearQueryOverrides() {
  const overrides = getQueryOverrides()
  Object.keys(overrides).forEach(k => delete overrides[k])
}

// ---------- Mock ALL dependencies ----------

vi.mock('lucide-react', () => {
  const S = () => null
  return { Users: S, MessageSquare: S, Shield: S, AlertTriangle: S, Search: S, MoreVertical: S, Ban: S, CheckCircle: S, Trash2: S, Bell: S }
})

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: any) => <div>{children}</div>,
  CardDescription: ({ children }: any) => <p>{children}</p>,
  CardHeader: ({ children }: any) => <div>{children}</div>,
  CardTitle: ({ children }: any) => <h3>{children}</h3>,
}))
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled }: any) => <button onClick={onClick} disabled={disabled}>{children}</button>,
}))
vi.mock('@/components/ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}))
vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}))
vi.mock('@/components/ui/label', () => ({
  Label: ({ children }: any) => <label>{children}</label>,
}))
vi.mock('@/components/ui/textarea', () => ({
  Textarea: (props: any) => <textarea {...props} />,
}))
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: any) => <div>{children}</div>,
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogDescription: ({ children }: any) => <p>{children}</p>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
}))
vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick }: any) => <div role="menuitem" onClick={onClick}>{children}</div>,
  DropdownMenuTrigger: ({ children }: any) => <div>{children}</div>,
}))
vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabsContent: ({ children }: any) => <div>{children}</div>,
  TabsList: ({ children }: any) => <div role="tablist">{children}</div>,
  TabsTrigger: ({ children, onClick }: any) => <button role="tab" onClick={onClick}>{children}</button>,
}))
vi.mock('@/components/ui/table', () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableCell: ({ children }: any) => <td>{children}</td>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
}))

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => '/admin',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

vi.mock('@/services/admin', () => ({
  adminService: {
    getStats: vi.fn(),
    getUsers: vi.fn(),
    getPosts: vi.fn(),
    banUser: vi.fn(),
    unbanUser: vi.fn(),
    deletePost: vi.fn(),
    sendNotification: vi.fn(),
    sendBulkNotification: vi.fn(),
  },
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
vi.mock('@/components/layout/AppLayout', () => ({
  AppLayout: ({ children }: any) => <div data-testid="app-layout">{children}</div>,
}))

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn((opts: any) => {
    const key = Array.isArray(opts.queryKey) ? opts.queryKey[0] : opts.queryKey
    const overrides = getQueryOverrides()
    if (overrides[key]) return overrides[key]
    if (key === 'admin-stats') return { data: mockStats, isLoading: false, error: null }
    if (key === 'admin-users') return { data: mockUsers, isLoading: false, error: null }
    if (key === 'admin-posts') return { data: mockPosts, isLoading: false, error: null }
    return { data: undefined, isLoading: false, error: null }
  }),
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}))

// Import page AFTER all mocks
import AdminPage from '../page'

function setAdmin() {
  localStorage.setItem('user', JSON.stringify({ id: 'admin1', name: 'Admin', role: 'admin' }))
}

function setNonAdmin() {
  localStorage.setItem('user', JSON.stringify({ id: 'u1', name: 'User', role: 'user' }))
}

describe('AdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    clearQueryOverrides()
  })

  afterEach(() => {
    localStorage.clear()
  })

  // ============ Auth ============

  it('redirects to /login when not logged in', () => {
    render(<AdminPage />)
    expect(mockPush).toHaveBeenCalledWith('/login')
  })

  it('redirects non-admin users to /dashboard', () => {
    setNonAdmin()
    render(<AdminPage />)
    expect(mockPush).toHaveBeenCalledWith('/dashboard')
  })

  it('renders nothing while checking auth (no user)', () => {
    const { container } = render(<AdminPage />)
    expect(container.textContent).toBe('')
  })

  it('allows admin and shows key elements', () => {
    setAdmin()
    render(<AdminPage />)
    expect(mockPush).not.toHaveBeenCalled()
    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Admin Access')).toBeInTheDocument()
    expect(screen.getByText('Manage users, moderate content, and monitor system')).toBeInTheDocument()
  })

  // ============ Stats ============

  it('displays stat values', () => {
    setAdmin()
    render(<AdminPage />)
    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText('Total Users')).toBeInTheDocument()
    expect(screen.getByText('45')).toBeInTheDocument()
    expect(screen.getByText('Total Posts')).toBeInTheDocument()
    expect(screen.getByText('117')).toBeInTheDocument()
    expect(screen.getByText('Active Users')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Banned Users')).toBeInTheDocument()
  })

  it('shows loading dots when stats are loading', () => {
    setAdmin()
    setQueryOverride('admin-stats', { data: undefined, isLoading: true, error: null })
    render(<AdminPage />)
    const dots = screen.getAllByText('...')
    expect(dots.length).toBeGreaterThanOrEqual(4)
  })

  it('shows zeros when stats are null', () => {
    setAdmin()
    setQueryOverride('admin-stats', { data: null, isLoading: false, error: null })
    render(<AdminPage />)
    const zeros = screen.getAllByText('0')
    expect(zeros.length).toBeGreaterThanOrEqual(3)
  })

  it('shows backend connection error when stats fail', () => {
    setAdmin()
    setQueryOverride('admin-stats', { data: undefined, isLoading: false, error: new Error('fail') })
    render(<AdminPage />)
    expect(screen.getByText('Backend Connection Error')).toBeInTheDocument()
  })

  it('shows error for users loading failure', () => {
    setAdmin()
    setQueryOverride('admin-users', { data: undefined, isLoading: false, error: new Error('Network Error') })
    render(<AdminPage />)
    expect(screen.getByText(/Error loading users/)).toBeInTheDocument()
  })

  it('shows error for posts loading failure', () => {
    setAdmin()
    setQueryOverride('admin-posts', { data: undefined, isLoading: false, error: new Error('API error') })
    render(<AdminPage />)
    expect(screen.getByText(/Error loading posts/)).toBeInTheDocument()
  })

  // ============ User Data ============

  it('displays user data', () => {
    setAdmin()
    render(<AdminPage />)
    // Names appear in both user table and post table, use getAllByText
    expect(screen.getAllByText('Ravi Kumar').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Priya Nair').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('9876543210')).toBeInTheDocument()
    expect(screen.getAllByText('Thrissur').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Ernakulam').length).toBeGreaterThanOrEqual(1)
  })

  it('shows Active and Banned badges', () => {
    setAdmin()
    render(<AdminPage />)
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Banned')).toBeInTheDocument()
  })

  it('shows user count', () => {
    setAdmin()
    render(<AdminPage />)
    expect(screen.getByText(/Total: 2/)).toBeInTheDocument()
  })

  it('shows loading state for users', () => {
    setAdmin()
    setQueryOverride('admin-users', { data: undefined, isLoading: true, error: null })
    render(<AdminPage />)
    expect(screen.getByText('Loading users...')).toBeInTheDocument()
  })

  it('shows empty state for users', () => {
    setAdmin()
    setQueryOverride('admin-users', { data: [], isLoading: false, error: null })
    render(<AdminPage />)
    expect(screen.getByText('No users found')).toBeInTheDocument()
  })

  // ============ Posts Data ============

  it('renders post data', () => {
    setAdmin()
    render(<AdminPage />)
    expect(screen.getByText('Rice prices rising')).toBeInTheDocument()
    expect(screen.getByText('Tomato harvest tips')).toBeInTheDocument()
    // Engagement text is split across child elements, use regex on container
    expect(screen.getByText('discussion')).toBeInTheDocument()
  })

  it('shows post loading state', () => {
    setAdmin()
    setQueryOverride('admin-posts', { data: undefined, isLoading: true, error: null })
    render(<AdminPage />)
    expect(screen.getByText('Loading posts...')).toBeInTheDocument()
  })

  it('shows empty post state', () => {
    setAdmin()
    setQueryOverride('admin-posts', { data: [], isLoading: false, error: null })
    render(<AdminPage />)
    expect(screen.getByText('No posts found')).toBeInTheDocument()
  })

  // ============ Dialog Content ============

  it('has dialog text in DOM', () => {
    setAdmin()
    render(<AdminPage />)
    // "Ban User" etc appear in menu items, dialog titles, and dialog buttons
    expect(screen.getAllByText('Ban User').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Unban User').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Delete Post').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/This action cannot be undone/)).toBeInTheDocument()
  })

  it('has broadcast elements', () => {
    setAdmin()
    render(<AdminPage />)
    // "Broadcast Notification" appears as both a button and dialog title
    expect(screen.getAllByText('Broadcast Notification').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Send Broadcast')).toBeInTheDocument()
  })
})
