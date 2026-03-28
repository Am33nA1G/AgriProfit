import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Navbar } from '../Navbar'

const mockPathname = vi.fn()
const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({ push: mockPush }),
  Link: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe('Navbar Component', () => {
  beforeEach(() => {
    mockPathname.mockReturnValue('/dashboard')
    mockPush.mockClear()
  })

  describe('Basic Rendering', () => {
    it('renders the navbar element', () => {
      const { container } = render(<Navbar />)
      
      const nav = container.querySelector('nav')
      expect(nav).toBeInTheDocument()
    })

    it('renders AgriProfit logo', () => {
      render(<Navbar />)
      
      expect(screen.getByText('AgriProfit')).toBeInTheDocument()
    })

    it('has sticky positioning', () => {
      const { container } = render(<Navbar />)
      
      const nav = container.querySelector('nav')
      expect(nav).toHaveClass('sticky')
    })

    it('has backdrop blur effect', () => {
      const { container } = render(<Navbar />)
      
      const nav = container.querySelector('nav')
      expect(nav).toHaveClass('backdrop-blur')
    })
  })

  describe('Search Functionality', () => {
    it('renders search input with correct placeholder', () => {
      render(<Navbar />)
      
      const searchInput = screen.getByPlaceholderText('Search commodities, mandis...')
      expect(searchInput).toBeInTheDocument()
      expect(searchInput).toHaveAttribute('type', 'text')
    })

    it('allows typing in search input', async () => {
      const user = userEvent.setup()
      render(<Navbar />)
      
      const searchInput = screen.getByPlaceholderText('Search commodities, mandis...')
      await user.type(searchInput, 'wheat')
      
      expect(searchInput).toHaveValue('wheat')
    })

    it('has search icon', () => {
      const { container } = render(<Navbar />)
      
      const searchIcon = container.querySelector('.lucide-search')
      expect(searchIcon).toBeInTheDocument()
    })

    it('search container has responsive classes for desktop display', () => {
      const { container } = render(<Navbar />)
      
      const searchContainer = container.querySelector('.hidden.md\\:flex')
      expect(searchContainer).toHaveClass('hidden')
      expect(searchContainer).toHaveClass('md:flex')
    })
  })

  describe('Notification Bell', () => {
    it('renders notification bell icon', () => {
      const { container } = render(<Navbar />)
      
      const bellIcon = container.querySelector('.lucide-bell')
      expect(bellIcon).toBeInTheDocument()
    })

    it('renders notification badge', () => {
      const { container } = render(<Navbar />)
      
      const badge = container.querySelector('.bg-red-500.rounded-full')
      expect(badge).toBeInTheDocument()
    })

    it('notification bell has link wrapper to notifications page', () => {
      const { container } = render(<Navbar />)
      
      const bellLink = container.querySelector('a[href="/notifications"]')
      expect(bellLink).toBeInTheDocument()
    })
  })

  describe('Mobile Menu', () => {
    it('has mobile menu button', () => {
      const { container } = render(<Navbar />)
      
      const menuButton = container.querySelector('.lg\\:hidden.p-2')
      expect(menuButton).toBeInTheDocument()
    })

    it('shows menu icon initially', () => {
      const { container } = render(<Navbar />)
      
      const menuIcon = container.querySelector('.lucide-menu')
      expect(menuIcon).toBeInTheDocument()
    })

    it('mobile logo has responsive class', () => {
      const { container } = render(<Navbar />)
      
      const mobileLogo = container.querySelector('a.lg\\:hidden.flex.items-center')
      expect(mobileLogo).toBeInTheDocument()
    })
  })

  describe('Layout Structure', () => {
    it('has border bottom', () => {
      const { container } = render(<Navbar />)
      
      const nav = container.querySelector('nav')
      expect(nav).toHaveClass('border-b')
    })

    it('has proper spacing classes', () => {
      const { container } = render(<Navbar />)
      
      const nav = container.querySelector('nav')
      expect(nav).toHaveClass('z-40')
    })

    it('contains flex container for layout', () => {
      const { container } = render(<Navbar />)
      
      const flexContainer = container.querySelector('.flex.items-center.justify-between')
      expect(flexContainer).toBeInTheDocument()
    })
  })
})
