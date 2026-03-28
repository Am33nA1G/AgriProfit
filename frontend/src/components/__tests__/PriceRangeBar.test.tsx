import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PriceRangeBar from '../PriceRangeBar'

describe('PriceRangeBar', () => {
    it('renders low, mid, and high prices', () => {
        render(<PriceRangeBar price_low={420} price_mid={510} price_high={590} />)
        expect(screen.getByText('₹420.00')).toBeInTheDocument()
        expect(screen.getByText('₹510.00')).toBeInTheDocument()
        expect(screen.getByText('₹590.00')).toBeInTheDocument()
    })

    it('shows Low, Mid, High labels when all values present', () => {
        render(<PriceRangeBar price_low={420} price_mid={510} price_high={590} />)
        expect(screen.getByText('Low')).toBeInTheDocument()
        expect(screen.getByText('Mid')).toBeInTheDocument()
        expect(screen.getByText('High')).toBeInTheDocument()
    })

    it('renders only mid when low and high are null', () => {
        render(<PriceRangeBar price_low={null} price_mid={510} price_high={null} />)
        expect(screen.getByText('₹510.00')).toBeInTheDocument()
        expect(screen.queryByText('Low')).not.toBeInTheDocument()
        expect(screen.queryByText('High')).not.toBeInTheDocument()
    })

    it('renders nothing when mid is null', () => {
        const { container } = render(
            <PriceRangeBar price_low={null} price_mid={null} price_high={null} />
        )
        expect(container.firstChild).toBeNull()
    })
})
