import { LightningElement, wire } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import { refreshApex } from '@salesforce/apex';
import getDashboardData from '@salesforce/apex/CampusEventsDashboardController.getDashboardData';

export default class CampusEventsHome extends NavigationMixin(LightningElement) {
    data;
    error;
    wiredDashboard;
    isRefreshing = false;
    isDark = false;

    connectedCallback() {
        try {
            this.isDark = window.localStorage.getItem('campus-theme') === 'dark';
        } catch (e) {
            this.isDark = false;
        }
    }

    @wire(getDashboardData)
    loadDashboard(result) {
        this.wiredDashboard = result;
        if (result.data) {
            this.data = result.data;
            this.error = undefined;
        } else if (result.error) {
            this.error = result.error;
            this.data = undefined;
        }
    }

    get shellClass() {
        return this.isDark ? 'shell theme-dark' : 'shell';
    }

    get themeIcon() {
        return this.isDark ? 'utility:light_bulb' : 'utility:night';
    }

    get themeLabel() {
        return this.isDark ? 'Use light theme' : 'Use dark theme';
    }

    get errorMessage() {
        return this.error?.body?.message || 'Campus Events data could not be loaded.';
    }

    get attendanceLabel() {
        return `${Number(this.data?.attendanceRate || 0).toFixed(1)}%`;
    }

    get statusBars() {
        return this.toBars(this.data?.eventsByStatus);
    }

    get departmentBars() {
        return this.toBars(this.data?.registrationsByDepartment);
    }

    toBars(items = []) {
        const max = Math.max(1, ...items.map((item) => Number(item.value) || 0));
        return items.map((item) => ({
            ...item,
            key: item.label,
            style: `width:${Math.max(5, Math.round((Number(item.value) || 0) * 100 / max))}%`
        }));
    }

    toggleTheme() {
        this.isDark = !this.isDark;
        try {
            window.localStorage.setItem('campus-theme', this.isDark ? 'dark' : 'light');
        } catch (e) {
            // Persistence is optional in restricted browser contexts.
        }
    }

    async refresh() {
        this.isRefreshing = true;
        try {
            await refreshApex(this.wiredDashboard);
        } finally {
            this.isRefreshing = false;
        }
    }

    navigateObject(event) {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName: event.currentTarget.dataset.object,
                actionName: event.currentTarget.dataset.action || 'list'
            }
        });
    }

    navigateRecord(event) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: event.currentTarget.dataset.id,
                actionName: 'view'
            }
        });
    }

    navigatePage(event) {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: { objectApiName: event.currentTarget.dataset.object, actionName: 'home' }
        });
    }
}
