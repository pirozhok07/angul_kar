import { Routes } from '@angular/router';

import { KataGroupsList }  from './kata-groups-list/kata-groups-list';

export const KATA_GROUPS_ROUTES: Routes = [
    {
        path: '',
        component: KataGroupsList
    }
];
