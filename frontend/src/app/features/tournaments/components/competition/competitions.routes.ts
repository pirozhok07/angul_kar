import { Routes } from '@angular/router';

import { Kumite }  from './kumite/kumite';
import { Kata }  from './kata/kata.js';

export const COMPETITIONS_ROUTES: Routes = [
    {
        path: 'kumite',
        component: Kumite
    },
    {
        path: 'kata',
        component: Kata
    }
];
