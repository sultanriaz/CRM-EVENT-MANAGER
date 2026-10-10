import { LightningElement, wire } from 'lwc';
import getInsights from '@salesforce/apex/FitnessInsightsController.getInsights';
import getTopTrainers from '@salesforce/apex/FitnessInsightsController.getTopTrainers';
import getRetention from '@salesforce/apex/FitnessInsightsController.getRetention';

export default class FitnessInsightsPanel extends LightningElement {
    insights = [];
    trainers = [];
    retention;

    @wire(getInsights)
    wiredInsights({ data }) {
        if (data) {
            this.insights = data.map((i, idx) => ({
                key: 'i' + idx,
                title: i.title,
                detail: i.detail,
                cls: 'insight insight-' + i.severity
            }));
        }
    }

    @wire(getTopTrainers)
    wiredTrainers({ data }) {
        if (data) {
            const max = Math.max(1, ...data.map((t) => t.attended));
            this.trainers = data.map((t, idx) => ({
                key: 't' + idx,
                name: t.name,
                attended: t.attended,
                rate: Number(t.rate).toFixed(0) + '% attendance',
                style: 'width:' + Math.max(4, Math.round((t.attended / max) * 100)) + '%'
            }));
        }
    }

    @wire(getRetention)
    wiredRetention({ data }) {
        if (data) this.retention = data;
    }

    get retentionPct() {
        return this.retention ? Number(this.retention.retentionRate).toFixed(0) : '0';
    }
    get ringDash() {
        const pct = this.retention ? Number(this.retention.retentionRate) : 0;
        const c = 2 * Math.PI * 45;
        return ((c * pct) / 100).toFixed(1) + ' ' + c.toFixed(1);
    }
    get retained() {
        return this.retention ? this.retention.retained : 0;
    }
    get priorActive() {
        return this.retention ? this.retention.priorActive : 0;
    }
    get atRisk() {
        return this.retention ? this.retention.atRisk : 0;
    }
    get hasInsights() {
        return this.insights.length > 0;
    }
}