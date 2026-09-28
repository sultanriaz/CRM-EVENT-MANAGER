import { LightningElement, wire } from 'lwc';
import { refreshApex } from '@salesforce/apex';
import getDashboardMetrics from '@salesforce/apex/FitnessDashboardController.getDashboardMetrics';
import getMonthlyRevenue from '@salesforce/apex/FitnessDashboardController.getMonthlyRevenue';
import getCityPerformance from '@salesforce/apex/FitnessDashboardController.getCityPerformance';
import getMemberGrowth from '@salesforce/apex/FitnessDashboardController.getMemberGrowth';

const compact = (v) => {
    const n = Number(v) || 0;
    if (n >= 1000000) return 'Rs. ' + (n / 1000000).toFixed(2) + 'M';
    if (n >= 1000) return 'Rs. ' + Math.round(n / 1000) + 'K';
    return 'Rs. ' + n;
};

export default class FitnessHubDashboard extends LightningElement {
    metrics;
    error;
    monthlyData = [];
    cityData = [];
    growthData = [];
    isRefreshing = false;
    wiredResults = {};

    @wire(getDashboardMetrics)
    wiredMetrics(result) {
        this.wiredResults.metrics = result;
        const { data, error } = result;
        if (data) {
            this.metrics = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.metrics = undefined;
        }
    }

    @wire(getMonthlyRevenue)
    wiredMonthly(result) {
        this.wiredResults.monthly = result;
        if (result.data) this.monthlyData = result.data;
    }

    @wire(getCityPerformance)
    wiredCities(result) {
        this.wiredResults.cities = result;
        if (result.data) this.cityData = result.data;
    }

    @wire(getMemberGrowth)
    wiredGrowth(result) {
        this.wiredResults.growth = result;
        if (result.data) this.growthData = result.data;
    }

    async handleRefresh() {
        this.isRefreshing = true;
        try {
            await Promise.all(Object.values(this.wiredResults).map((r) => refreshApex(r)));
        } finally {
            this.isRefreshing = false;
        }
    }

    get refreshLabel() {
        return this.isRefreshing ? 'Refreshing...' : 'Refresh';
    }

    get errorMessage() {
        return (this.error && this.error.body && this.error.body.message)
            || 'Unable to load dashboard metrics';
    }

    get revenue() {
        return this.metrics ? 'Rs. ' + Number(this.metrics.totalRevenue).toLocaleString('en-PK') : 'Loading...';
    }
    get members() {
        return this.metrics ? this.metrics.activeMembers : 0;
    }
    get attendance() {
        return this.metrics ? Number(this.metrics.attendanceRate).toFixed(1) + '%' : '0%';
    }
    get classes() {
        return this.metrics ? this.metrics.totalClasses : 0;
    }
    get trainers() {
        return this.metrics ? this.metrics.totalTrainers : 0;
    }
    get vipMembers() {
        return this.metrics ? this.metrics.vipMembers : 0;
    }
    get averageValue() {
        return this.metrics ? 'Rs. ' + Math.round(Number(this.metrics.averageMemberValue)).toLocaleString('en-PK') : 'Rs. 0';
    }
    get todaysBookings() {
        return this.metrics ? this.metrics.todaysBookings : 0;
    }

    get monthlyBars() {
        const max = Math.max(1, ...this.monthlyData.map((m) => Number(m.revenue) || 0));
        return this.monthlyData.map((m) => ({
            key: m.label,
            label: m.label.split(' ')[0],
            valueLabel: compact(m.revenue),
            style: 'height:' + Math.max(2, Math.round(((Number(m.revenue) || 0) / max) * 100)) + '%'
        }));
    }

    get cityBars() {
        const max = Math.max(1, ...this.cityData.map((c) => Number(c.revenue) || 0));
        return this.cityData.map((c) => ({
            key: c.city,
            city: c.city,
            revenueLabel: compact(c.revenue),
            meta: c.members + ' members | ' + c.bookings + ' bookings',
            style: 'width:' + Math.max(2, Math.round(((Number(c.revenue) || 0) / max) * 100)) + '%'
        }));
    }

    get growthPoints() {
        const n = this.growthData.length;
        const max = Math.max(1, ...this.growthData.map((g) => Number(g.totalMembers) || 0));
        return this.growthData.map((g, i) => ({
            key: g.label,
            label: g.label.split(' ')[0],
            total: g.totalMembers,
            cx: n > 1 ? 15 + (i * 270) / (n - 1) : 150,
            cy: 100 - ((Number(g.totalMembers) || 0) / max) * 80
        }));
    }
    get growthLine() {
        return this.growthPoints.map((p) => p.cx + ',' + p.cy).join(' ');
    }
    get growthArea() {
        const pts = this.growthPoints;
        if (!pts.length) return '';
        return this.growthLine + ' ' + pts[pts.length - 1].cx + ',110 ' + pts[0].cx + ',110';
    }
}