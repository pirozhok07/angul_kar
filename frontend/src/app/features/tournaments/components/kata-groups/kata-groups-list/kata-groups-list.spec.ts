import { ComponentFixture, TestBed } from '@angular/core/testing';
import { KataGroupsList } from './kata-groups-list';

describe('KataGroupsList', () => {
  let component: KataGroupsList;
  let fixture: ComponentFixture<KataGroupsList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KataGroupsList],
    }).compileComponents();

    fixture = TestBed.createComponent(KataGroupsList);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
