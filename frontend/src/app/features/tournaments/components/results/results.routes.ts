import { Routes } from '@angular/router';

import { ResultsList }  from '../results/results-list/results-list.js';

export const RESULTS_ROUTES: Routes = [
    {
        path: '',
        component: ResultsList
    },
];
