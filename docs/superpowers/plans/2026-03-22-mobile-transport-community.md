# Mobile Transport & Community Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Transport and Community tabs to the React Native mobile app and restructure navigation from 4 to 5 tabs (dropping Analyze as a tab, making it accessible via Inventory header).

**Architecture:** Three layers — services (API wrappers), screens (UI), navigation (stack + tab wiring). Services are written first and imported by screens. Navigation is rewired last to avoid breaking the running app mid-build. Each task is independently committable.

**Tech Stack:** React Native (Expo), TypeScript, `@react-navigation/native-stack`, `@tanstack/react-query`, `lucide-react-native`, Zustand (`useAuthStore`), project `api` axios client (`mobile/src/lib/api.ts`).

**Token reference** (from `mobile/src/theme/tokens.ts`):
- Spacing: `spacing[1]`=4, `spacing[2]`=8, `spacing[3]`=12, `spacing[4]`=16, `spacing[6]`=24, `spacing[8]`=32, `spacing[10]`=40
- Colors: `colors.foreground` (body text), `colors.muted`, `colors.primary`, `colors.background`, `colors.card`, `colors.border`, `colors.error`, `colors.warning`, `colors.success`, `colors.surface`
- Shadows: `shadows.sm`, `shadows.card`, `shadows.modal`
- Radii: `radii.sm`=4, `radii.md`=8, `radii.lg`=12, `radii.xl`=16, `radii.full`=9999

**Spec:** `docs/superpowers/specs/2026-03-22-mobile-transport-community-design.md`

---

## Task 1: Static data — STATE_DISTRICTS

**Files:**
- Create: `mobile/src/data/stateDistricts.ts`

- [ ] **Step 1: Create the file**

```ts
// mobile/src/data/stateDistricts.ts
// Static map of Indian states → districts.
// Source: frontend/src/app/transport/page.tsx STATE_DISTRICTS

export const STATE_DISTRICTS: Record<string, string[]> = {
    "Kerala": ["Thiruvananthapuram", "Kollam", "Alappuzha", "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"],
    "Tamil Nadu": ["Chennai", "Chengalpattu", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Thanjavur", "Dindigul", "Krishnagiri", "Kancheepuram", "Tiruvannamalai", "Cuddalore", "Villupuram", "Nagapattinam", "Tiruppur", "Namakkal", "Karur", "Dharmapuri", "Nilgiris", "Kanyakumari"],
    "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru", "Hubli-Dharwad", "Belagavi", "Tumakuru", "Davangere", "Ballari", "Shivamogga", "Kalaburagi", "Hassan"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Kadapa", "Tirupati", "Anantapur", "Rajahmundry", "Kakinada", "Eluru", "Ongole"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Ramagundam", "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet", "Siddipet", "Medak"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Thane", "Satara", "Sangli", "Ahmednagar", "Jalgaon", "Amravati"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Mehsana", "Bharuch", "Morbi", "Kutch"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Satna", "Rewa", "Ratlam", "Chhindwara", "Dewas", "Khandwa", "Vidisha"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner", "Ajmer", "Bharatpur", "Alwar", "Sikar", "Pali", "Bhilwara", "Nagaur", "Chittorgarh"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Allahabad", "Bareilly", "Aligarh", "Moradabad", "Ghaziabad", "Noida", "Gorakhpur", "Mathura"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia", "Arrah", "Begusarai", "Katihar", "Munger", "Chhapra", "Samastipur"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol", "Bardhaman", "Malda", "Kharagpur", "Haldia", "Baharampur", "Raiganj", "Krishnanagar"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri", "Balasore", "Bhadrak", "Baripada", "Jharsuguda", "Koraput", "Angul"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Pathankot", "Hoshiarpur", "Moga", "Firozpur", "Kapurthala", "Sangrur"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Yamunanagar", "Rohtak", "Hisar", "Karnal", "Sonipat", "Panchkula", "Bhiwani", "Sirsa"],
    "Goa": ["North Goa", "South Goa"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg", "Rajnandgaon", "Jagdalpur", "Raigarh", "Ambikapur", "Dhamtari"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh", "Deoghar", "Giridih", "Ramgarh", "Dumka", "Chaibasa"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Rishikesh", "Haldwani", "Roorkee", "Kashipur", "Rudrapur", "Nainital", "Almora", "Pithoragarh"],
    "Himachal Pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Kullu", "Bilaspur", "Hamirpur", "Una", "Kangra", "Palampur"],
    "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tinsukia", "Tezpur", "Bongaigaon", "Karimganj", "Sivasagar"],
    "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Pasighat", "Tawang", "Ziro", "Bomdila", "Along", "Tezu", "Roing", "Changlang"],
    "Manipur": ["Imphal East", "Imphal West", "Thoubal", "Bishnupur", "Churachandpur", "Senapati", "Ukhrul", "Chandel"],
    "Meghalaya": ["Shillong", "Tura", "Jowai", "Nongstoin", "Williamnagar", "Baghmara", "Resubelpara"],
    "Mizoram": ["Aizawl", "Lunglei", "Champhai", "Serchhip", "Kolasib", "Lawngtlai", "Mamit", "Saiha"],
    "Nagaland": ["Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha", "Zunheboto", "Mon", "Phek"],
    "Tripura": ["Agartala", "Udaipur", "Dharmanagar", "Kailashahar", "Khowai", "Ambassa", "Belonia", "Sabroom"],
    "Sikkim": ["Gangtok", "Namchi", "Gyalshing", "Mangan", "Rangpo", "Singtam", "Jorethang"],
};

export const STATES = Object.keys(STATE_DISTRICTS).sort();
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/data/stateDistricts.ts
git commit -m "feat(mobile): add static STATE_DISTRICTS data file"
```

---

## Task 2: Transport service

**Files:**
- Create: `mobile/src/services/transport.ts`

- [ ] **Step 1: Create the service**

```ts
// mobile/src/services/transport.ts
// Transport mandi-comparison API service.

import api from '../lib/api';

export interface CostBreakdown {
    transport_cost: number;
    toll_cost: number;
    loading_cost: number;
    unloading_cost: number;
    mandi_fee: number;
    commission: number;
    additional_cost: number;
    driver_bata: number;
    cleaner_bata: number;
    halt_cost: number;
    breakdown_reserve: number;
    permit_cost: number;
    rto_buffer: number;
    loading_hamali: number;
    unloading_hamali: number;
    total_cost: number;
}

export interface MandiComparison {
    mandi_name: string;
    district: string;
    state: string;
    distance_km: number;
    price_per_kg: number;
    gross_revenue: number;
    net_profit: number;
    roi_percentage: number;
    profit_per_kg: number;
    vehicle_type: string;
    vehicle_capacity_kg: number;
    trips_required: number;
    travel_time_hours: number;
    spoilage_percent: number;
    verdict: 'excellent' | 'good' | 'marginal' | 'not_viable';
    verdict_reason: string;
    costs: CostBreakdown;
    risk_score: number;
    confidence_score: number;
    economic_warning: string | null;
}

export interface TransportCompareParams {
    commodity: string;
    quantity_kg: number;
    source_state: string;
    source_district: string;
}

export const transportService = {
    async compare(params: TransportCompareParams): Promise<MandiComparison[]> {
        const { data } = await api.post('/transport/compare', params);
        return data.comparisons;
    },
};
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/services/transport.ts
git commit -m "feat(mobile): add transport API service"
```

---

## Task 3: Community service

**Files:**
- Create: `mobile/src/services/community.ts`

- [ ] **Step 1: Create the service**

```ts
// mobile/src/services/community.ts
// Community posts API service — mirrors frontend/src/services/community.ts

import api from '../lib/api';

export type PostType = 'discussion' | 'question' | 'tip' | 'announcement' | 'alert';

export const POST_TYPE_LABELS: Record<PostType, string> = {
    discussion: 'General',
    question: 'Question',
    tip: 'Tip',
    announcement: 'Announcement',
    alert: 'Alert',
};

// Hex colours for badge backgrounds
export const POST_TYPE_COLORS: Record<PostType, string> = {
    discussion: '#3b82f6',
    question: '#22c55e',
    tip: '#a855f7',
    announcement: '#f97316',
    alert: '#ef4444',
};

export interface CommunityPost {
    id: string;
    title: string;
    content: string;
    user_id: string;
    post_type: PostType;
    district: string | null;
    image_url: string | null;
    likes_count: number;
    replies_count: number;
    user_has_liked: boolean;
    created_at: string;
    updated_at: string;
    author_name?: string;
}

export interface CommunityReply {
    id: string;
    post_id: string;
    user_id: string;
    content: string;
    created_at: string;
    author_name?: string;
}

export const communityService = {
    // Backend returns paginated envelope { items, total, skip, limit } — extract .items
    async listPosts(params?: { post_type?: PostType; limit?: number }): Promise<CommunityPost[]> {
        const { data } = await api.get('/community/posts', { params });
        return data.items;
    },

    async createPost(payload: { title: string; content: string; post_type: PostType }): Promise<CommunityPost> {
        const { data } = await api.post('/community/posts', payload);
        return data;
    },

    async updatePost(id: string, payload: { title?: string; content?: string; post_type?: PostType }): Promise<CommunityPost> {
        const { data } = await api.put(`/community/posts/${id}`, payload);
        return data;
    },

    async deletePost(id: string): Promise<void> {
        await api.delete(`/community/posts/${id}`);
    },

    async addUpvote(post_id: string): Promise<void> {
        await api.post(`/community/posts/${post_id}/upvote`);
    },

    async removeUpvote(post_id: string): Promise<void> {
        await api.delete(`/community/posts/${post_id}/upvote`);
    },

    async getReplies(post_id: string): Promise<CommunityReply[]> {
        const { data } = await api.get(`/community/posts/${post_id}/replies`);
        return data;
    },

    // Note: endpoint is /reply (singular), not /replies
    async addReply(post_id: string, content: string): Promise<CommunityReply> {
        const { data } = await api.post(`/community/posts/${post_id}/reply`, { content });
        return data;
    },
};

export function formatRelativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/services/community.ts
git commit -m "feat(mobile): add community API service"
```

---

## Task 4: Transport screen

**Files:**
- Create: `mobile/src/screens/transport/TransportScreen.tsx`

- [ ] **Step 1: Create the screen**

```tsx
// mobile/src/screens/transport/TransportScreen.tsx
// Find best mandis to sell a commodity — form + ranked results.

import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    ScrollView,
    Modal,
    StyleSheet,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Truck, ChevronDown, ChevronUp, Search, Edit2 } from 'lucide-react-native';
import { useQuery } from '@tanstack/react-query';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import { transportService, type MandiComparison } from '../../services/transport';
import { STATE_DISTRICTS, STATES } from '../../data/stateDistricts';
import api from '../../lib/api';

// ─── Constants ────────────────────────────────────────────────────────────────

const VERDICT_COLORS: Record<MandiComparison['verdict'], string> = {
    excellent: '#16a34a',
    good: '#2563eb',
    marginal: '#d97706',
    not_viable: '#dc2626',
};

const VERDICT_BG: Record<MandiComparison['verdict'], string> = {
    excellent: '#dcfce7',
    good: '#dbeafe',
    marginal: '#fef3c7',
    not_viable: '#fee2e2',
};

const VERDICT_LABELS: Record<MandiComparison['verdict'], string> = {
    excellent: 'Excellent',
    good: 'Good',
    marginal: 'Marginal',
    not_viable: 'Not Viable',
};

// ─── CostRow ──────────────────────────────────────────────────────────────────

function CostRow({ label, value }: { label: string; value: number }) {
    if (value === 0) return null;
    return (
        <View style={styles.costRow}>
            <Text style={styles.costLabel}>{label}</Text>
            <Text style={styles.costValue}>₹{value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</Text>
        </View>
    );
}

// ─── MandiCard ────────────────────────────────────────────────────────────────

function MandiCard({ item }: { item: MandiComparison }) {
    const [expanded, setExpanded] = useState(false);
    const profitColor = item.net_profit >= 0 ? colors.success : colors.error;

    return (
        <TouchableOpacity style={styles.card} onPress={() => setExpanded(e => !e)} activeOpacity={0.85}>
            <View style={styles.cardTop}>
                <View style={styles.cardLeft}>
                    <Text style={styles.mandiName}>{item.mandi_name}</Text>
                    <Text style={styles.mandiMeta}>{item.district}, {item.state}</Text>
                    <Text style={styles.mandiMeta}>
                        {item.distance_km.toFixed(0)} km · {item.travel_time_hours.toFixed(1)}h
                    </Text>
                </View>
                <View style={styles.cardRight}>
                    <View style={[styles.verdictBadge, { backgroundColor: VERDICT_BG[item.verdict] }]}>
                        <Text style={[styles.verdictText, { color: VERDICT_COLORS[item.verdict] }]}>
                            {VERDICT_LABELS[item.verdict]}
                        </Text>
                    </View>
                    <Text style={[styles.profitAmount, { color: profitColor }]}>
                        ₹{Math.abs(item.net_profit).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        {item.net_profit < 0 ? ' loss' : ''}
                    </Text>
                    <Text style={styles.roiText}>ROI {item.roi_percentage.toFixed(1)}%</Text>
                </View>
            </View>

            <View style={styles.expandHint}>
                {expanded ? <ChevronUp size={14} color={colors.muted} /> : <ChevronDown size={14} color={colors.muted} />}
                <Text style={styles.expandHintText}>{expanded ? 'Hide costs' : 'Show costs'}</Text>
            </View>

            {expanded && (
                <View style={styles.costBreakdown}>
                    <CostRow label="Freight" value={item.costs.transport_cost} />
                    <CostRow label="Loading hamali" value={item.costs.loading_hamali} />
                    <CostRow label="Unloading hamali" value={item.costs.unloading_hamali} />
                    <CostRow label="Toll" value={item.costs.toll_cost} />
                    <CostRow label="Mandi fee" value={item.costs.mandi_fee} />
                    <CostRow label="Commission" value={item.costs.commission} />
                    <CostRow label="Driver bata" value={item.costs.driver_bata} />
                    <CostRow label="Permit" value={item.costs.permit_cost} />
                    <View style={[styles.costRow, styles.costRowTotal]}>
                        <Text style={styles.costLabelBold}>Total costs</Text>
                        <Text style={styles.costValueBold}>₹{item.costs.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</Text>
                    </View>
                    {item.economic_warning ? (
                        <Text style={styles.warning}>⚠ {item.economic_warning}</Text>
                    ) : null}
                </View>
            )}
        </TouchableOpacity>
    );
}

// ─── PickerModal ──────────────────────────────────────────────────────────────

function PickerModal({
    visible, title, options, selected, onSelect, onClose,
}: {
    visible: boolean; title: string; options: string[];
    selected: string; onSelect: (v: string) => void; onClose: () => void;
}) {
    return (
        <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
            <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={onClose} />
            <View style={styles.pickerSheet}>
                <Text style={styles.pickerTitle}>{title}</Text>
                <FlatList
                    data={options}
                    keyExtractor={item => item}
                    renderItem={({ item }) => (
                        <TouchableOpacity
                            style={[styles.pickerItem, item === selected && styles.pickerItemSelected]}
                            onPress={() => { onSelect(item); onClose(); }}
                        >
                            <Text style={[styles.pickerItemText, item === selected && styles.pickerItemTextSelected]}>
                                {item}
                            </Text>
                        </TouchableOpacity>
                    )}
                />
            </View>
        </Modal>
    );
}

// ─── Screen ───────────────────────────────────────────────────────────────────

export function TransportScreen() {
    const [commodity, setCommodity] = useState('');
    const [commoditySearch, setCommoditySearch] = useState('');
    const [showCommodityDropdown, setShowCommodityDropdown] = useState(false);
    const [quantity, setQuantity] = useState('');
    const [unit, setUnit] = useState<'kg' | 'quintal'>('kg');
    const [sourceState, setSourceState] = useState('Kerala');
    const [sourceDistrict, setSourceDistrict] = useState('');
    const [showStatePicker, setShowStatePicker] = useState(false);
    const [showDistrictPicker, setShowDistrictPicker] = useState(false);
    const [results, setResults] = useState<MandiComparison[] | null>(null);
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});

    const districts = STATE_DISTRICTS[sourceState] ?? [];

    const { data: commoditySuggestions } = useQuery({
        queryKey: ['commodity-search', commoditySearch],
        queryFn: async () => {
            if (commoditySearch.length < 2) return [];
            const { data } = await api.get('/commodities/search/', { params: { q: commoditySearch, limit: 20 } });
            return data as { id: string; name: string }[];
        },
        enabled: commoditySearch.length >= 2,
        staleTime: 60000,
    });

    function validate(): boolean {
        const e: Record<string, string> = {};
        if (!commodity) e.commodity = 'Select a commodity';
        if (!quantity || isNaN(Number(quantity)) || Number(quantity) <= 0) {
            e.quantity = 'Enter a valid quantity';
        } else {
            const qty_kg = Number(quantity) * (unit === 'quintal' ? 100 : 1);
            if (qty_kg > 50000) e.quantity = 'Maximum 50,000 kg (500 quintals)';
        }
        if (!sourceDistrict) e.district = 'Select a district';
        setErrors(e);
        return Object.keys(e).length === 0;
    }

    async function handleSearch() {
        if (!validate()) return;
        setLoading(true);
        try {
            const qty_kg = Number(quantity) * (unit === 'quintal' ? 100 : 1);
            const data = await transportService.compare({
                commodity,
                quantity_kg: qty_kg,
                source_state: sourceState,
                source_district: sourceDistrict,
            });
            setResults(data);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            Alert.alert('Error', msg ?? 'Could not reach server. Check your connection.');
        } finally {
            setLoading(false);
        }
    }

    // ── Form View ─────────────────────────────────────────────────────────────
    if (results === null) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.header}>
                    <Truck size={20} color={colors.primary} />
                    <Text style={styles.headerTitle}>Find Best Mandi</Text>
                </View>

                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
                    <ScrollView style={styles.scroll} contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled">

                        {/* Commodity */}
                        <Text style={styles.label}>Commodity</Text>
                        <View>
                            <View style={styles.inputRow}>
                                <Search size={16} color={colors.muted} style={{ marginLeft: spacing[3] }} />
                                <TextInput
                                    style={styles.inputWithIcon}
                                    placeholder="Search commodity…"
                                    value={commoditySearch}
                                    onChangeText={v => {
                                        setCommoditySearch(v);
                                        if (v !== commodity) setCommodity('');
                                        setShowCommodityDropdown(true);
                                    }}
                                    onFocus={() => setShowCommodityDropdown(true)}
                                    placeholderTextColor={colors.muted}
                                />
                            </View>
                            {errors.commodity ? <Text style={styles.errorText}>{errors.commodity}</Text> : null}
                            {showCommodityDropdown && (commoditySuggestions?.length ?? 0) > 0 && (
                                <View style={styles.dropdown}>
                                    {(commoditySuggestions ?? []).map(c => (
                                        <TouchableOpacity
                                            key={c.id}
                                            style={styles.dropdownItem}
                                            onPress={() => {
                                                setCommodity(c.name);
                                                setCommoditySearch(c.name);
                                                setShowCommodityDropdown(false);
                                            }}
                                        >
                                            <Text style={styles.dropdownItemText}>{c.name}</Text>
                                        </TouchableOpacity>
                                    ))}
                                </View>
                            )}
                        </View>

                        {/* Quantity */}
                        <Text style={styles.label}>Quantity</Text>
                        <View style={styles.quantityRow}>
                            <TextInput
                                style={[styles.input, styles.quantityInput]}
                                placeholder="0"
                                value={quantity}
                                onChangeText={setQuantity}
                                keyboardType="numeric"
                                placeholderTextColor={colors.muted}
                            />
                            <TouchableOpacity
                                style={[styles.unitToggle, unit === 'kg' && styles.unitToggleActive]}
                                onPress={() => setUnit('kg')}
                            >
                                <Text style={[styles.unitToggleText, unit === 'kg' && styles.unitToggleTextActive]}>kg</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[styles.unitToggle, unit === 'quintal' && styles.unitToggleActive]}
                                onPress={() => setUnit('quintal')}
                            >
                                <Text style={[styles.unitToggleText, unit === 'quintal' && styles.unitToggleTextActive]}>qtl</Text>
                            </TouchableOpacity>
                        </View>
                        {errors.quantity ? <Text style={styles.errorText}>{errors.quantity}</Text> : null}

                        {/* Source State */}
                        <Text style={styles.label}>Source State</Text>
                        <TouchableOpacity style={styles.picker} onPress={() => setShowStatePicker(true)}>
                            <Text style={styles.pickerValue}>{sourceState}</Text>
                            <ChevronDown size={16} color={colors.muted} />
                        </TouchableOpacity>

                        {/* Source District */}
                        <Text style={styles.label}>Source District</Text>
                        <TouchableOpacity
                            style={[styles.picker, !sourceState && styles.pickerDisabled]}
                            onPress={() => sourceState ? setShowDistrictPicker(true) : undefined}
                            disabled={!sourceState}
                        >
                            <Text style={[styles.pickerValue, !sourceDistrict && { color: colors.muted }]}>
                                {sourceDistrict || 'Select district…'}
                            </Text>
                            <ChevronDown size={16} color={colors.muted} />
                        </TouchableOpacity>
                        {errors.district ? <Text style={styles.errorText}>{errors.district}</Text> : null}

                        <TouchableOpacity
                            style={[styles.searchBtn, loading && styles.searchBtnDisabled]}
                            onPress={handleSearch}
                            disabled={loading}
                        >
                            {loading
                                ? <ActivityIndicator color="#fff" size="small" />
                                : <Text style={styles.searchBtnText}>Find Best Mandis</Text>
                            }
                        </TouchableOpacity>
                    </ScrollView>
                </KeyboardAvoidingView>

                <PickerModal
                    visible={showStatePicker} title="Select State" options={STATES} selected={sourceState}
                    onSelect={v => { setSourceState(v); setSourceDistrict(''); }}
                    onClose={() => setShowStatePicker(false)}
                />
                <PickerModal
                    visible={showDistrictPicker} title="Select District" options={districts} selected={sourceDistrict}
                    onSelect={setSourceDistrict} onClose={() => setShowDistrictPicker(false)}
                />
            </SafeAreaView>
        );
    }

    // ── Results View ──────────────────────────────────────────────────────────
    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.resultsHeader}>
                <Text style={styles.resultsTitle} numberOfLines={1}>{commodity} · {quantity} {unit}</Text>
                <TouchableOpacity style={styles.editBtn} onPress={() => setResults(null)}>
                    <Edit2 size={14} color={colors.primary} />
                    <Text style={styles.editBtnText}>Edit</Text>
                </TouchableOpacity>
            </View>

            {results.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyText}>No mandis found for this search.</Text>
                </View>
            ) : (
                <FlatList
                    data={results}
                    keyExtractor={item => `${item.mandi_name}-${item.district}`}
                    renderItem={({ item }) => <MandiCard item={item} />}
                    contentContainerStyle={styles.listContent}
                />
            )}
        </SafeAreaView>
    );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    header: { flexDirection: 'row', alignItems: 'center', gap: spacing[2], paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: spacing[3] },
    headerTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    scroll: { flex: 1 },
    formContent: { padding: spacing[4], gap: spacing[3] },
    label: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: 2 },
    input: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    inputRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card },
    inputWithIcon: { flex: 1, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground },
    quantityRow: { flexDirection: 'row', gap: spacing[2] },
    quantityInput: { flex: 1 },
    unitToggle: { paddingHorizontal: spacing[3], paddingVertical: spacing[2], borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card },
    unitToggleActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    unitToggleText: { fontSize: typography.fontSize.sm, color: colors.muted },
    unitToggleTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    picker: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], backgroundColor: colors.card },
    pickerDisabled: { opacity: 0.5 },
    pickerValue: { fontSize: typography.fontSize.base, color: colors.foreground },
    dropdown: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, backgroundColor: colors.card, maxHeight: 180, ...shadows.card },
    dropdownItem: { paddingHorizontal: spacing[3], paddingVertical: spacing[2] },
    dropdownItemText: { fontSize: typography.fontSize.base, color: colors.foreground },
    searchBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2] },
    searchBtnDisabled: { opacity: 0.6 },
    searchBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
    errorText: { fontSize: typography.fontSize.xs, color: colors.error, marginTop: 2 },
    resultsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing[4], paddingVertical: spacing[3], borderBottomWidth: 1, borderBottomColor: colors.border },
    resultsTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, flex: 1 },
    editBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    editBtnText: { fontSize: typography.fontSize.sm, color: colors.primary },
    listContent: { padding: spacing[4], gap: spacing[3] },
    emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    emptyText: { color: colors.muted, fontSize: typography.fontSize.base },
    card: { backgroundColor: colors.card, borderRadius: radii.lg, padding: spacing[3], borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    cardTop: { flexDirection: 'row', justifyContent: 'space-between' },
    cardLeft: { flex: 1 },
    cardRight: { alignItems: 'flex-end', gap: 4 },
    mandiName: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    mandiMeta: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 2 },
    verdictBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    verdictText: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold },
    profitAmount: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold },
    roiText: { fontSize: typography.fontSize.xs, color: colors.muted },
    expandHint: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, marginTop: spacing[2], paddingTop: spacing[2], borderTopWidth: 1, borderTopColor: colors.border },
    expandHintText: { fontSize: typography.fontSize.xs, color: colors.muted },
    costBreakdown: { marginTop: spacing[2], gap: 4 },
    costRow: { flexDirection: 'row', justifyContent: 'space-between' },
    costRowTotal: { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 4, paddingTop: 4 },
    costLabel: { fontSize: typography.fontSize.xs, color: colors.muted },
    costValue: { fontSize: typography.fontSize.xs, color: colors.foreground },
    costLabelBold: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    costValueBold: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground },
    warning: { fontSize: typography.fontSize.xs, color: colors.warning, marginTop: 4 },
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    pickerSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, maxHeight: '60%', paddingBottom: spacing[8] },
    pickerTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, padding: spacing[4], borderBottomWidth: 1, borderBottomColor: colors.border },
    pickerItem: { paddingHorizontal: spacing[4], paddingVertical: spacing[3] },
    pickerItemSelected: { backgroundColor: colors.primaryLight },
    pickerItemText: { fontSize: typography.fontSize.base, color: colors.foreground },
    pickerItemTextSelected: { color: colors.primary, fontWeight: typography.fontWeight.medium },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/screens/transport/TransportScreen.tsx
git commit -m "feat(mobile): add TransportScreen"
```

---

## Task 5: Community feed screen

**Files:**
- Create: `mobile/src/screens/community/CommunityFeedScreen.tsx`

- [ ] **Step 1: Create the screen**

```tsx
// mobile/src/screens/community/CommunityFeedScreen.tsx
// Community post feed with category filter chips, sort, and create post FAB.

import React, { useState, useCallback } from 'react';
import {
    View,
    Text,
    FlatList,
    ScrollView,
    TouchableOpacity,
    TextInput,
    Modal,
    StyleSheet,
    ActivityIndicator,
    Alert,
    RefreshControl,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Plus, Heart, MessageCircle, ChevronDown } from 'lucide-react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import {
    communityService,
    type CommunityPost,
    type PostType,
    POST_TYPE_LABELS,
    POST_TYPE_COLORS,
    formatRelativeTime,
} from '../../services/community';
import type { CommunityStackParamList } from '../../navigation/CommunityStack';

type Props = {
    navigation: NativeStackNavigationProp<CommunityStackParamList, 'CommunityFeed'>;
};

const CHIPS: { label: string; value: PostType | undefined }[] = [
    { label: 'All', value: undefined },
    { label: 'General', value: 'discussion' },
    { label: 'Tips', value: 'tip' },
    { label: 'Questions', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

type SortKey = 'created_at' | 'likes_count' | 'replies_count';
const SORT_OPTIONS: { label: string; key: SortKey }[] = [
    { label: 'Most Recent', key: 'created_at' },
    { label: 'Most Upvoted', key: 'likes_count' },
    { label: 'Most Replies', key: 'replies_count' },
];

const CREATE_CATEGORIES: { label: string; value: PostType }[] = [
    { label: 'General', value: 'discussion' },
    { label: 'Tip', value: 'tip' },
    { label: 'Question', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

function PostCard({ post, onPress }: { post: CommunityPost; onPress: () => void }) {
    const badgeColor = POST_TYPE_COLORS[post.post_type] ?? '#6b7280';
    return (
        <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.85}>
            <View style={styles.cardHeader}>
                <View style={[styles.badge, { backgroundColor: badgeColor + '22' }]}>
                    <Text style={[styles.badgeText, { color: badgeColor }]}>
                        {POST_TYPE_LABELS[post.post_type] ?? post.post_type}
                    </Text>
                </View>
                <Text style={styles.timestamp}>{formatRelativeTime(post.created_at)}</Text>
            </View>
            <Text style={styles.postTitle} numberOfLines={2}>{post.title}</Text>
            <View style={styles.cardFooter}>
                <Text style={styles.authorText}>{post.author_name ?? 'Farmer'}</Text>
                <View style={styles.statsRow}>
                    <Heart size={13} color={colors.muted} />
                    <Text style={styles.statText}>{post.likes_count}</Text>
                    <MessageCircle size={13} color={colors.muted} style={{ marginLeft: spacing[2] }} />
                    <Text style={styles.statText}>{post.replies_count}</Text>
                </View>
            </View>
        </TouchableOpacity>
    );
}

export function CommunityFeedScreen({ navigation }: Props) {
    const [posts, setPosts] = useState<CommunityPost[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeChip, setActiveChip] = useState<PostType | undefined>(undefined);
    const [sortKey, setSortKey] = useState<SortKey>('created_at');
    const [showSortMenu, setShowSortMenu] = useState(false);

    const [showCreate, setShowCreate] = useState(false);
    const [createTitle, setCreateTitle] = useState('');
    const [createContent, setCreateContent] = useState('');
    const [createCategory, setCreateCategory] = useState<PostType>('discussion');
    const [createErrors, setCreateErrors] = useState<Record<string, string>>({});
    const [submitting, setSubmitting] = useState(false);

    const sortedPosts = [...posts].sort((a, b) => {
        if (sortKey === 'created_at') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        return (b[sortKey] as number) - (a[sortKey] as number);
    });

    const fetchPosts = useCallback(async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true); else setLoading(true);
        setError(null);
        try {
            const data = await communityService.listPosts({ post_type: activeChip, limit: 100 });
            setPosts(data);
        } catch {
            setError('Failed to load posts. Pull to retry.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [activeChip]);

    React.useEffect(() => { fetchPosts(); }, [fetchPosts]);

    function validateCreate(): boolean {
        const e: Record<string, string> = {};
        if (!createTitle.trim()) e.title = 'Title is required';
        else if (createTitle.length > 200) e.title = 'Max 200 characters';
        if (!createContent.trim()) e.content = 'Content is required';
        else if (createContent.trim().length < 10) e.content = 'Min 10 characters';
        else if (createContent.length > 2000) e.content = 'Max 2000 characters';
        setCreateErrors(e);
        return Object.keys(e).length === 0;
    }

    async function handleCreate() {
        if (!validateCreate()) return;
        setSubmitting(true);
        try {
            const post = await communityService.createPost({
                title: createTitle.trim(),
                content: createContent.trim(),
                post_type: createCategory,
            });
            setPosts(prev => [post, ...prev]);
            setShowCreate(false);
            setCreateTitle(''); setCreateContent(''); setCreateCategory('discussion');
        } catch {
            Alert.alert('Error', 'Failed to create post. Please try again.');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Community</Text>
                <TouchableOpacity style={styles.sortBtn} onPress={() => setShowSortMenu(v => !v)}>
                    <ChevronDown size={14} color={colors.primary} />
                    <Text style={styles.sortBtnText}>{SORT_OPTIONS.find(s => s.key === sortKey)?.label}</Text>
                </TouchableOpacity>
            </View>

            {showSortMenu && (
                <View style={styles.sortMenu}>
                    {SORT_OPTIONS.map(opt => (
                        <TouchableOpacity
                            key={opt.key}
                            style={[styles.sortMenuItem, opt.key === sortKey && styles.sortMenuItemActive]}
                            onPress={() => { setSortKey(opt.key); setShowSortMenu(false); }}
                        >
                            <Text style={[styles.sortMenuItemText, opt.key === sortKey && styles.sortMenuItemTextActive]}>
                                {opt.label}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>
            )}

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
                {CHIPS.map(chip => (
                    <TouchableOpacity
                        key={chip.label}
                        style={[styles.chip, chip.value === activeChip && styles.chipActive]}
                        onPress={() => setActiveChip(chip.value)}
                    >
                        <Text style={[styles.chipText, chip.value === activeChip && styles.chipTextActive]}>
                            {chip.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {loading ? (
                <ActivityIndicator style={{ marginTop: spacing[10] }} color={colors.primary} />
            ) : error ? (
                <View style={styles.errorState}>
                    <Text style={styles.errorStateText}>{error}</Text>
                    <TouchableOpacity onPress={() => fetchPosts()}>
                        <Text style={styles.retryText}>Retry</Text>
                    </TouchableOpacity>
                </View>
            ) : (
                <FlatList
                    data={sortedPosts}
                    keyExtractor={item => item.id}
                    renderItem={({ item }) => (
                        <PostCard post={item} onPress={() => navigation.navigate('PostDetail', { post_id: item.id })} />
                    )}
                    contentContainerStyle={styles.listContent}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={() => fetchPosts(true)} tintColor={colors.primary} />
                    }
                    ListEmptyComponent={<Text style={styles.emptyText}>No posts yet. Be the first!</Text>}
                />
            )}

            <TouchableOpacity style={styles.fab} onPress={() => setShowCreate(true)}>
                <Plus size={24} color="#fff" />
            </TouchableOpacity>

            <Modal visible={showCreate} animationType="slide" transparent onRequestClose={() => setShowCreate(false)}>
                <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowCreate(false)} />
                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.createSheet}>
                    <Text style={styles.sheetTitle}>New Post</Text>

                    <Text style={styles.createLabel}>Title</Text>
                    <TextInput
                        style={styles.createInput}
                        placeholder="What's on your mind?"
                        value={createTitle}
                        onChangeText={setCreateTitle}
                        placeholderTextColor={colors.muted}
                        maxLength={200}
                    />
                    {createErrors.title ? <Text style={styles.fieldError}>{createErrors.title}</Text> : null}

                    <Text style={styles.createLabel}>Content</Text>
                    <TextInput
                        style={[styles.createInput, styles.contentInput]}
                        placeholder="Share details…"
                        value={createContent}
                        onChangeText={setCreateContent}
                        multiline
                        textAlignVertical="top"
                        placeholderTextColor={colors.muted}
                        maxLength={2000}
                    />
                    {createErrors.content ? <Text style={styles.fieldError}>{createErrors.content}</Text> : null}

                    <Text style={styles.createLabel}>Category</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>
                        {CREATE_CATEGORIES.map(cat => (
                            <TouchableOpacity
                                key={cat.value}
                                style={[styles.catChip, cat.value === createCategory && styles.catChipActive]}
                                onPress={() => setCreateCategory(cat.value)}
                            >
                                <Text style={[styles.catChipText, cat.value === createCategory && styles.catChipTextActive]}>
                                    {cat.label}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </ScrollView>

                    <TouchableOpacity
                        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
                        onPress={handleCreate}
                        disabled={submitting}
                    >
                        {submitting
                            ? <ActivityIndicator color="#fff" size="small" />
                            : <Text style={styles.submitBtnText}>Post</Text>
                        }
                    </TouchableOpacity>
                </KeyboardAvoidingView>
            </Modal>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing[4], paddingVertical: spacing[3] },
    headerTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground },
    sortBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    sortBtnText: { fontSize: typography.fontSize.sm, color: colors.primary },
    sortMenu: { position: 'absolute', top: 56, right: spacing[4], backgroundColor: colors.card, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border, zIndex: 10, ...shadows.card },
    sortMenuItem: { paddingHorizontal: spacing[4], paddingVertical: spacing[2] },
    sortMenuItemActive: { backgroundColor: colors.primaryLight },
    sortMenuItemText: { fontSize: typography.fontSize.sm, color: colors.foreground },
    sortMenuItemTextActive: { color: colors.primary, fontWeight: typography.fontWeight.medium },
    chips: { paddingHorizontal: spacing[4], gap: spacing[2], paddingBottom: spacing[2] },
    chip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    chipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    chipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    listContent: { padding: spacing[4], gap: spacing[3], paddingBottom: 80 },
    errorState: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[3] },
    errorStateText: { color: colors.muted, textAlign: 'center' },
    retryText: { color: colors.primary, fontWeight: typography.fontWeight.medium },
    emptyText: { textAlign: 'center', color: colors.muted, marginTop: spacing[10] },
    card: { backgroundColor: colors.card, borderRadius: radii.lg, padding: spacing[3], borderWidth: 1, borderColor: colors.border, ...shadows.sm },
    cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
    badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    badgeText: { fontSize: 11, fontWeight: typography.fontWeight.semibold },
    timestamp: { fontSize: typography.fontSize.xs, color: colors.muted },
    postTitle: { fontSize: typography.fontSize.base, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: spacing[2] },
    cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    authorText: { fontSize: typography.fontSize.xs, color: colors.muted },
    statsRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    statText: { fontSize: typography.fontSize.xs, color: colors.muted },
    fab: { position: 'absolute', bottom: spacing[6], right: spacing[4], backgroundColor: colors.primary, width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center', ...shadows.modal },
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    createSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, padding: spacing[4], gap: spacing[2] },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    createLabel: { fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.foreground, marginBottom: 2 },
    createInput: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    contentInput: { height: 100, paddingTop: spacing[2] },
    fieldError: { fontSize: typography.fontSize.xs, color: colors.error, marginTop: 2 },
    categoryRow: { gap: spacing[2] },
    catChip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    catChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    catChipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    catChipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    submitBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2] },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/screens/community/CommunityFeedScreen.tsx
git commit -m "feat(mobile): add CommunityFeedScreen"
```

---

## Task 6: Post detail screen

**Files:**
- Create: `mobile/src/screens/community/PostDetailScreen.tsx`

- [ ] **Step 1: Create the screen**

```tsx
// mobile/src/screens/community/PostDetailScreen.tsx
// Full post view with upvote toggle, replies, and owner edit/delete.

import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    TouchableOpacity,
    Image,
    StyleSheet,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
    ActionSheetIOS,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Heart, MessageCircle, MoreVertical, Send } from 'lucide-react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import { colors, typography, spacing, radii, shadows } from '../../theme/tokens';
import {
    communityService,
    type CommunityPost,
    type CommunityReply,
    type PostType,
    POST_TYPE_LABELS,
    POST_TYPE_COLORS,
    formatRelativeTime,
} from '../../services/community';
import { useAuthStore } from '../../store/authStore';
import api from '../../lib/api';
import type { CommunityStackParamList } from '../../navigation/CommunityStack';

type Props = {
    navigation: NativeStackNavigationProp<CommunityStackParamList, 'PostDetail'>;
    route: RouteProp<CommunityStackParamList, 'PostDetail'>;
};

const CREATE_CATEGORIES: { label: string; value: PostType }[] = [
    { label: 'General', value: 'discussion' },
    { label: 'Tip', value: 'tip' },
    { label: 'Question', value: 'question' },
    { label: 'Alert', value: 'alert' },
];

export function PostDetailScreen({ navigation, route }: Props) {
    const { post_id } = route.params;
    const currentUserId = useAuthStore(s => s.user?.id);

    const [post, setPost] = useState<CommunityPost | null>(null);
    const [replies, setReplies] = useState<CommunityReply[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [liked, setLiked] = useState(false);
    const [likesCount, setLikesCount] = useState(0);
    const [replyText, setReplyText] = useState('');
    const [submittingReply, setSubmittingReply] = useState(false);

    // Edit state
    const [editTitle, setEditTitle] = useState('');
    const [editContent, setEditContent] = useState('');
    const [editCategory, setEditCategory] = useState<PostType>('discussion');
    const [showEditSheet, setShowEditSheet] = useState(false);
    const [submittingEdit, setSubmittingEdit] = useState(false);

    useEffect(() => { loadPost(); }, [post_id]);

    async function loadPost() {
        setLoading(true);
        setError(null);
        try {
            const [fetchedPost, fetchedReplies] = await Promise.all([
                api.get(`/community/posts/${post_id}`).then(r => r.data as CommunityPost),
                communityService.getReplies(post_id),
            ]);
            setPost(fetchedPost);
            setLiked(fetchedPost.user_has_liked);
            setLikesCount(fetchedPost.likes_count);
            setReplies(fetchedReplies);
        } catch {
            setError('Failed to load post.');
        } finally {
            setLoading(false);
        }
    }

    async function handleUpvote() {
        if (!post) return;
        const prevLiked = liked;
        const prevCount = likesCount;
        setLiked(!liked);
        setLikesCount(c => prevLiked ? c - 1 : c + 1);
        try {
            if (prevLiked) await communityService.removeUpvote(post_id);
            else await communityService.addUpvote(post_id);
        } catch {
            setLiked(prevLiked);
            setLikesCount(prevCount);
            Alert.alert('Failed to update');
        }
    }

    async function handleAddReply() {
        if (!replyText.trim()) return;
        setSubmittingReply(true);
        try {
            const reply = await communityService.addReply(post_id, replyText.trim());
            setReplies(prev => [...prev, reply]);
            setReplyText('');
        } catch {
            Alert.alert('Error', 'Failed to post reply.');
        } finally {
            setSubmittingReply(false);
        }
    }

    function openOwnerMenu() {
        if (Platform.OS === 'ios') {
            ActionSheetIOS.showActionSheetWithOptions(
                { options: ['Cancel', 'Edit', 'Delete'], cancelButtonIndex: 0, destructiveButtonIndex: 2 },
                idx => { if (idx === 1) openEdit(); if (idx === 2) confirmDelete(); }
            );
        } else {
            Alert.alert('Post Options', undefined, [
                { text: 'Edit', onPress: openEdit },
                { text: 'Delete', style: 'destructive', onPress: confirmDelete },
                { text: 'Cancel', style: 'cancel' },
            ]);
        }
    }

    function openEdit() {
        if (!post) return;
        setEditTitle(post.title);
        setEditContent(post.content);
        setEditCategory(post.post_type);
        setShowEditSheet(true);
    }

    async function handleEdit() {
        if (!editTitle.trim() || editContent.trim().length < 10) {
            Alert.alert('Validation', 'Title and content (min 10 chars) are required.');
            return;
        }
        setSubmittingEdit(true);
        try {
            const updated = await communityService.updatePost(post_id, {
                title: editTitle.trim(),
                content: editContent.trim(),
                post_type: editCategory,
            });
            setPost(updated);
            setShowEditSheet(false);
        } catch {
            Alert.alert('Error', 'Failed to update post.');
        } finally {
            setSubmittingEdit(false);
        }
    }

    function confirmDelete() {
        Alert.alert('Delete Post', 'Are you sure?', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: async () => {
                try {
                    await communityService.deletePost(post_id);
                    navigation.goBack();
                } catch {
                    Alert.alert('Error', 'Failed to delete post.');
                }
            }},
        ]);
    }

    // Register ⋮ header button once post loads
    useEffect(() => {
        if (post && currentUserId && post.user_id === currentUserId) {
            navigation.setOptions({
                headerRight: () => (
                    <TouchableOpacity onPress={openOwnerMenu} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                        <MoreVertical size={20} color={colors.foreground} />
                    </TouchableOpacity>
                ),
            });
        }
    }, [post, currentUserId]);

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <ActivityIndicator style={{ marginTop: spacing[10] }} color={colors.primary} />
            </SafeAreaView>
        );
    }

    if (error || !post) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <Text style={styles.errorText}>{error ?? 'Post not found.'}</Text>
            </SafeAreaView>
        );
    }

    const badgeColor = POST_TYPE_COLORS[post.post_type] ?? '#6b7280';

    return (
        <SafeAreaView style={styles.safeArea} edges={['bottom']}>
            <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
                <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
                    <View style={[styles.badge, { backgroundColor: badgeColor + '22', alignSelf: 'flex-start', marginBottom: spacing[2] }]}>
                        <Text style={[styles.badgeText, { color: badgeColor }]}>
                            {POST_TYPE_LABELS[post.post_type]}
                        </Text>
                    </View>
                    <Text style={styles.postTitle}>{post.title}</Text>
                    <Text style={styles.postMeta}>{post.author_name ?? 'Farmer'} · {formatRelativeTime(post.created_at)}</Text>
                    <Text style={styles.postContent}>{post.content}</Text>

                    {post.image_url ? (
                        <Image source={{ uri: post.image_url }} style={styles.postImage} resizeMode="cover" />
                    ) : null}

                    <TouchableOpacity style={styles.upvoteBtn} onPress={handleUpvote}>
                        <Heart
                            size={18}
                            color={liked ? colors.error : colors.muted}
                            fill={liked ? colors.error : 'none'}
                        />
                        <Text style={[styles.upvoteCount, liked && { color: colors.error }]}>{likesCount}</Text>
                    </TouchableOpacity>

                    <View style={styles.repliesDivider}>
                        <MessageCircle size={14} color={colors.muted} />
                        <Text style={styles.repliesHeader}>{replies.length} {replies.length === 1 ? 'reply' : 'replies'}</Text>
                    </View>

                    {replies.map(reply => (
                        <View key={reply.id} style={styles.replyCard}>
                            <Text style={styles.replyAuthor}>{reply.author_name ?? 'Farmer'}</Text>
                            <Text style={styles.replyContent}>{reply.content}</Text>
                            <Text style={styles.replyTime}>{formatRelativeTime(reply.created_at)}</Text>
                        </View>
                    ))}
                </ScrollView>

                <View style={styles.replyBar}>
                    <TextInput
                        style={styles.replyInput}
                        placeholder="Write a reply…"
                        value={replyText}
                        onChangeText={setReplyText}
                        placeholderTextColor={colors.muted}
                        multiline
                    />
                    <TouchableOpacity
                        style={[styles.sendBtn, (!replyText.trim() || submittingReply) && styles.sendBtnDisabled]}
                        onPress={handleAddReply}
                        disabled={!replyText.trim() || submittingReply}
                    >
                        {submittingReply
                            ? <ActivityIndicator size="small" color="#fff" />
                            : <Send size={16} color="#fff" />
                        }
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>

            {/* Edit sheet */}
            {showEditSheet && (
                <View style={StyleSheet.absoluteFillObject as object}>
                    <TouchableOpacity style={styles.editBackdrop} activeOpacity={1} onPress={() => setShowEditSheet(false)} />
                    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.editSheet}>
                        <Text style={styles.sheetTitle}>Edit Post</Text>
                        <TextInput style={styles.editInput} value={editTitle} onChangeText={setEditTitle} placeholder="Title" placeholderTextColor={colors.muted} />
                        <TextInput style={[styles.editInput, styles.editContentInput]} value={editContent} onChangeText={setEditContent} multiline textAlignVertical="top" placeholder="Content" placeholderTextColor={colors.muted} />
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>
                            {CREATE_CATEGORIES.map(cat => (
                                <TouchableOpacity key={cat.value} style={[styles.catChip, cat.value === editCategory && styles.catChipActive]} onPress={() => setEditCategory(cat.value)}>
                                    <Text style={[styles.catChipText, cat.value === editCategory && styles.catChipTextActive]}>{cat.label}</Text>
                                </TouchableOpacity>
                            ))}
                        </ScrollView>
                        <TouchableOpacity style={[styles.submitBtn, submittingEdit && styles.submitBtnDisabled]} onPress={handleEdit} disabled={submittingEdit}>
                            {submittingEdit ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.submitBtnText}>Save</Text>}
                        </TouchableOpacity>
                    </KeyboardAvoidingView>
                </View>
            )}
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: colors.background },
    scroll: { flex: 1 },
    scrollContent: { padding: spacing[4], paddingBottom: spacing[8] },
    badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radii.sm },
    badgeText: { fontSize: 11, fontWeight: typography.fontWeight.semibold },
    postTitle: { fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: 4 },
    postMeta: { fontSize: typography.fontSize.xs, color: colors.muted, marginBottom: spacing[3] },
    postContent: { fontSize: typography.fontSize.base, color: colors.foreground, lineHeight: 22, marginBottom: spacing[3] },
    postImage: { width: '100%', height: 200, borderRadius: radii.lg, marginBottom: spacing[3] },
    upvoteBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingVertical: spacing[2], marginBottom: spacing[4] },
    upvoteCount: { fontSize: typography.fontSize.base, color: colors.muted, fontWeight: typography.fontWeight.medium },
    repliesDivider: { flexDirection: 'row', alignItems: 'center', gap: 6, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing[3], marginBottom: spacing[3] },
    repliesHeader: { fontSize: typography.fontSize.sm, color: colors.muted, fontWeight: typography.fontWeight.medium },
    replyCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing[3], marginBottom: spacing[2], borderWidth: 1, borderColor: colors.border },
    replyAuthor: { fontSize: typography.fontSize.xs, fontWeight: typography.fontWeight.semibold, color: colors.foreground, marginBottom: 2 },
    replyContent: { fontSize: typography.fontSize.base, color: colors.foreground },
    replyTime: { fontSize: typography.fontSize.xs, color: colors.muted, marginTop: 4 },
    replyBar: { flexDirection: 'row', alignItems: 'flex-end', gap: spacing[2], padding: spacing[3], borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.background },
    replyInput: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card, maxHeight: 80 },
    sendBtn: { backgroundColor: colors.primary, width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
    sendBtnDisabled: { opacity: 0.4 },
    errorText: { color: colors.error, textAlign: 'center', marginTop: spacing[10] },
    editBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
    editSheet: { backgroundColor: colors.background, borderTopLeftRadius: radii.xl, borderTopRightRadius: radii.xl, padding: spacing[4], gap: spacing[2] },
    sheetTitle: { fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.bold, color: colors.foreground, marginBottom: spacing[2] },
    editInput: { borderWidth: 1, borderColor: colors.border, borderRadius: radii.md, paddingHorizontal: spacing[3], paddingVertical: spacing[2], fontSize: typography.fontSize.base, color: colors.foreground, backgroundColor: colors.card },
    editContentInput: { height: 100, paddingTop: spacing[2] },
    categoryRow: { gap: spacing[2] },
    catChip: { paddingHorizontal: spacing[3], paddingVertical: 6, borderRadius: radii.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
    catChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
    catChipText: { fontSize: typography.fontSize.sm, color: colors.muted },
    catChipTextActive: { color: '#fff', fontWeight: typography.fontWeight.medium },
    submitBtn: { backgroundColor: colors.primary, borderRadius: radii.md, paddingVertical: spacing[3], alignItems: 'center', marginTop: spacing[2] },
    submitBtnDisabled: { opacity: 0.6 },
    submitBtnText: { color: '#fff', fontWeight: typography.fontWeight.semibold, fontSize: typography.fontSize.base },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/src/screens/community/PostDetailScreen.tsx
git commit -m "feat(mobile): add PostDetailScreen"
```

---

## Task 7: Stack navigators

**Files:**
- Create: `mobile/src/navigation/InventoryStack.tsx`
- Create: `mobile/src/navigation/CommunityStack.tsx`

- [ ] **Step 1: Create InventoryStack**

```tsx
// mobile/src/navigation/InventoryStack.tsx
import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../theme/tokens';
import { InventoryScreen } from '../screens/inventory/InventoryScreen';
import { InventoryAnalysisScreen } from '../screens/inventory/InventoryAnalysisScreen';

export type InventoryStackParamList = {
    Inventory: undefined;
    InventoryAnalysis: undefined;
};

const Stack = createNativeStackNavigator<InventoryStackParamList>();

export function InventoryStack() {
    return (
        <Stack.Navigator>
            <Stack.Screen name="Inventory" component={InventoryScreen} options={{ headerShown: false }} />
            <Stack.Screen
                name="InventoryAnalysis"
                component={InventoryAnalysisScreen}
                options={{
                    title: 'Inventory Analysis',
                    headerBackTitle: 'Back',
                    headerTintColor: colors.primary,
                }}
            />
        </Stack.Navigator>
    );
}
```

- [ ] **Step 2: Create CommunityStack**

```tsx
// mobile/src/navigation/CommunityStack.tsx
import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../theme/tokens';
import { CommunityFeedScreen } from '../screens/community/CommunityFeedScreen';
import { PostDetailScreen } from '../screens/community/PostDetailScreen';

export type CommunityStackParamList = {
    CommunityFeed: undefined;
    PostDetail: { post_id: string };
};

const Stack = createNativeStackNavigator<CommunityStackParamList>();

export function CommunityStack() {
    return (
        <Stack.Navigator>
            <Stack.Screen name="CommunityFeed" component={CommunityFeedScreen} options={{ headerShown: false }} />
            <Stack.Screen
                name="PostDetail"
                component={PostDetailScreen}
                options={{
                    title: 'Post',
                    headerBackTitle: 'Back',
                    headerTintColor: colors.primary,
                }}
            />
        </Stack.Navigator>
    );
}
```

- [ ] **Step 3: Commit**

```bash
git add mobile/src/navigation/InventoryStack.tsx mobile/src/navigation/CommunityStack.tsx
git commit -m "feat(mobile): add InventoryStack and CommunityStack navigators"
```

---

## Task 8: Fix InventoryAnalysisScreen — remove inline headers

The screen has two `<View style={styles.header}>` blocks that will double-render inside a native stack with `headerShown: true`. Remove both.

**Files:**
- Modify: `mobile/src/screens/inventory/InventoryAnalysisScreen.tsx`

- [ ] **Step 1: Remove the empty-state header block**

Find and remove this exact block (inside the early-return `items.length === 0` branch):
```tsx
<View style={styles.header}>
    <Text style={styles.pageTitle}>Analysis</Text>
    <Text style={styles.pageSubtitle}>Inventory breakdown & insights</Text>
</View>
```

- [ ] **Step 2: Remove the populated-state header block**

Find and remove this exact block (in the main return, after the opening `<SafeAreaView>`):
```tsx
{/* Header */}
<View style={styles.header}>
    <Text style={styles.pageTitle}>Analysis</Text>
    <Text style={styles.pageSubtitle}>
        {items.length} {items.length === 1 ? 'crop' : 'crops'} · Est. value ₹{totalValue.toLocaleString('en-IN')}
    </Text>
</View>
```

- [ ] **Step 3: Commit**

```bash
git add mobile/src/screens/inventory/InventoryAnalysisScreen.tsx
git commit -m "fix(mobile): remove inline header from InventoryAnalysisScreen for native stack"
```

---

## Task 9: Update InventoryScreen — add Analyze button

**Files:**
- Modify: `mobile/src/screens/inventory/InventoryScreen.tsx`

The existing header has a left `<View>` (title + subtitle) and a right `<TouchableOpacity>` (the "+" add button). Wrap the right side in a row to add "Analyze →" next to "+".

- [ ] **Step 1: Add navigation prop type and imports**

At the top of the file, after existing imports, add:
```tsx
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { InventoryStackParamList } from '../../navigation/InventoryStack';

type Props = {
    navigation: NativeStackNavigationProp<InventoryStackParamList, 'Inventory'>;
};
```

Change the function signature from:
```tsx
export function InventoryScreen() {
```
to:
```tsx
export function InventoryScreen({ navigation }: Props) {
```

- [ ] **Step 2: Update the header — wrap right side in a row**

The current header right side is a single `<TouchableOpacity style={styles.addButton}>`. Replace it with a wrapping `<View>` containing both buttons:

Replace:
```tsx
<TouchableOpacity style={styles.addButton} onPress={openAdd}>
    <Plus size={20} color={colors.background} />
</TouchableOpacity>
```

With:
```tsx
<View style={styles.headerActions}>
    <TouchableOpacity style={styles.analyzeBtn} onPress={() => navigation.navigate('InventoryAnalysis')}>
        <Text style={styles.analyzeBtnText}>Analyze →</Text>
    </TouchableOpacity>
    <TouchableOpacity style={styles.addButton} onPress={openAdd}>
        <Plus size={20} color={colors.background} />
    </TouchableOpacity>
</View>
```

- [ ] **Step 3: Add new styles to StyleSheet.create**

Add these two entries to the existing `StyleSheet.create({...})`:
```tsx
headerActions: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
analyzeBtn: { paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
analyzeBtnText: { fontSize: typography.fontSize.sm, color: colors.primary, fontWeight: typography.fontWeight.medium },
```

- [ ] **Step 4: Commit**

```bash
git add mobile/src/screens/inventory/InventoryScreen.tsx
git commit -m "feat(mobile): add Analyze button to InventoryScreen header"
```

---

## Task 10: Rewire MainTabs

Do this only after Tasks 1–9 are complete.

**Files:**
- Modify: `mobile/src/navigation/MainTabs.tsx`

- [ ] **Step 1: Replace the entire file content**

```tsx
// mobile/src/navigation/MainTabs.tsx
// Bottom tab navigator with 5 tabs: Inventory, Forecast, Transport, Community, Sales.

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigatorScreenParams } from '@react-navigation/native';
import { Archive, TrendingUp, Truck, Users, ShoppingCart } from 'lucide-react-native';
import { colors, typography } from '../theme/tokens';
import { InventoryStack, type InventoryStackParamList } from './InventoryStack';
import { CommunityStack, type CommunityStackParamList } from './CommunityStack';
import { ForecastScreen } from '../screens/forecast/ForecastScreen';
import { TransportScreen } from '../screens/transport/TransportScreen';
import { SalesScreen } from '../screens/sales/SalesScreen';

export type MainTabsParamList = {
    Inventory: NavigatorScreenParams<InventoryStackParamList>;
    Forecast: undefined;
    Transport: undefined;
    Community: NavigatorScreenParams<CommunityStackParamList>;
    Sales: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

const ICON_SIZE = 22;

export function MainTabs() {
    return (
        <Tab.Navigator
            screenOptions={{
                headerShown: false,
                tabBarActiveTintColor: colors.primary,
                tabBarInactiveTintColor: colors.muted,
                tabBarStyle: {
                    backgroundColor: colors.background,
                    borderTopColor: colors.border,
                    borderTopWidth: 1,
                    height: 64,
                    paddingBottom: 10,
                    paddingTop: 6,
                },
                tabBarLabelStyle: {
                    fontSize: typography.fontSize.xs,
                    fontWeight: typography.fontWeight.medium,
                },
            }}
        >
            <Tab.Screen
                name="Inventory"
                component={InventoryStack}
                options={{ tabBarIcon: ({ color }) => <Archive size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Forecast"
                component={ForecastScreen}
                options={{ tabBarIcon: ({ color }) => <TrendingUp size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Transport"
                component={TransportScreen}
                options={{ tabBarIcon: ({ color }) => <Truck size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Community"
                component={CommunityStack}
                options={{ tabBarIcon: ({ color }) => <Users size={ICON_SIZE} color={color} /> }}
            />
            <Tab.Screen
                name="Sales"
                component={SalesScreen}
                options={{ tabBarIcon: ({ color }) => <ShoppingCart size={ICON_SIZE} color={color} /> }}
            />
        </Tab.Navigator>
    );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd mobile && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add mobile/src/navigation/MainTabs.tsx
git commit -m "feat(mobile): rewire MainTabs — 5 tabs with Transport and Community"
```

---

## Task 11: Manual smoke test

```bash
cd mobile && npx expo start
```

- [ ] 5 tabs visible: Inventory, Forecast, Transport, Community, Sales (no Analyze tab)
- [ ] Inventory "Analyze →" button → InventoryAnalysis screen with native back button, no double header
- [ ] Transport form: pick commodity, enter quantity, pick state + district, search → results with cards; tap card → cost breakdown; "Edit" → form restored
- [ ] Community: posts load, chips filter feed, sort reorders, pull-to-refresh works; FAB → create sheet → submit → post appears
- [ ] Post Detail: full content, upvote toggles heart, replies load, reply input sends
