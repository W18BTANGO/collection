import { Injectable, Logger } from  //todo
import axios from 'axios';
import CONFIGS from '../../local.env';

const // define Dtos

@Injectable()
export class getPriceDataService {
    private readonly logger = new Logger(getPriceDataService.name);
    private housingDataApiDetails: {
        dataSourceUrl: string;
        // other parameters needed to hit the endpoint
    }
    // other variables to initialise


    constructor() {
        this.housingDataApiDetails = {
            "dataSourceUrl": CONFIGS.
        }
    }

    async doSomething(): Promise<dto> {
        return "hello world.";
    }
}