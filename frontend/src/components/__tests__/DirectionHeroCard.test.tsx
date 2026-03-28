import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

vi.mock('lucide-react', () => {
    const S = ({ className }: { className?: string }) => <svg className={className} />
    return { TrendingUp: S, TrendingDown: S, ArrowRight: S, Lock: S }
})

import DirectionHeroCard from '../DirectionHeroCard'

describe('DirectionHeroCard', () => {
    it('shows RISING for up direction', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={12}
                model_version="v5"
                r2_score={0.84}
            />
        )
        expect(screen.getByText('RISING')).toBeInTheDocument()
        expect(screen.getByText(/Prices expected to rise/)).toBeInTheDocument()
    })

    it('shows FALLING for down direction', () => {
        render(
            <DirectionHeroCard
                direction="down"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText('FALLING')).toBeInTheDocument()
        expect(screen.getByText(/Prices expected to fall/)).toBeInTheDocument()
    })

    it('shows STABLE for flat direction', () => {
        render(
            <DirectionHeroCard
                direction="flat"
                confidence_colour="Yellow"
                horizon_days={7}
                mape_pct={28}
                model_version="legacy"
                r2_score={null}
            />
        )
        expect(screen.getByText('STABLE')).toBeInTheDocument()
        expect(screen.getByText(/Prices holding steady/)).toBeInTheDocument()
    })

    it('shows UNCERTAIN and warning for Red confidence regardless of direction', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Red"
                horizon_days={7}
                mape_pct={55}
                model_version="legacy"
                r2_score={null}
            />
        )
        expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
        expect(screen.getByText(/Do not use for financial decisions/)).toBeInTheDocument()
    })

    it('shows UNCERTAIN for uncertain direction', () => {
        render(
            <DirectionHeroCard
                direction="uncertain"
                confidence_colour="Yellow"
                horizon_days={7}
                mape_pct={null}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText('UNCERTAIN')).toBeInTheDocument()
    })

    it('shows mape_pct when provided', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={12}
                model_version={null}
                r2_score={null}
            />
        )
        expect(screen.getByText(/±12%/)).toBeInTheDocument()
    })

    it('shows R² when positive', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version="v5"
                r2_score={0.84}
            />
        )
        expect(screen.getByText(/R² 0.84/)).toBeInTheDocument()
    })

    it('does not show R² when negative', () => {
        render(
            <DirectionHeroCard
                direction="up"
                confidence_colour="Green"
                horizon_days={7}
                mape_pct={null}
                model_version="v5"
                r2_score={-0.1}
            />
        )
        expect(screen.queryByText(/R²/)).not.toBeInTheDocument()
    })
})
