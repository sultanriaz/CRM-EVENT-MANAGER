import { api, LightningElement } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
const FITNESS = 'c__Community_Fitness_Wellness_Hub';
const CAMPUS = 'c__Campus_Events_Manager';
export default class WorkspaceSwitcher extends NavigationMixin(LightningElement) {
    @api currentApp = FITNESS;
    appOptions = [
        { label: 'Fitness Hub — CRM', value: FITNESS },
        { label: 'Campus Events Manager', value: CAMPUS }
    ];
    handleChange(event) {
        const target = event.detail.value;
        if (![FITNESS, CAMPUS].includes(target) || target === this.currentApp) return;
        this[NavigationMixin.Navigate]({ type: 'standard__app', attributes: { appTarget: target } });
    }
}
